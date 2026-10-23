# Tests for SitePulse. None of these need the internet.
#
# Run them from the sitepulse folder with:
#   py -m pytest
#
# pytest finds every function whose name starts with "test_" and runs it.
# Each "assert" is a check: if it's False, that test fails and pytest
# shows you what went wrong.

import csv
import json

# pytest is the testing library from requirements.txt.
import pytest

# Import our own program so we can test its functions directly.
import sitepulse


def make_row(url, status_code, is_up, response_ms):
    """Build one fake history.csv row, shaped like csv.DictReader gives it.

    Everything is text, because that's what comes out of a CSV file.
    """
    return {
        "timestamp": "2026-10-23 12:00:00",
        "url": url,
        "status_code": status_code,
        "is_up": is_up,
        "response_ms": response_ms,
    }


# ---------- calculate_uptime ----------


def test_uptime_three_out_of_four():
    assert sitepulse.calculate_uptime(3, 4) == 75.0


def test_uptime_all_up():
    assert sitepulse.calculate_uptime(4, 4) == 100.0


def test_uptime_all_down():
    assert sitepulse.calculate_uptime(0, 4) == 0.0


def test_uptime_with_no_checks_does_not_divide_by_zero():
    assert sitepulse.calculate_uptime(0, 0) == 0.0


def test_uptime_with_decimals():
    # 2 / 3 * 100 is 66.666..., which can't be stored exactly.
    # pytest.approx allows for tiny rounding differences.
    assert sitepulse.calculate_uptime(2, 3) == pytest.approx(66.667, abs=0.001)


# ---------- summarize_history ----------


def test_summarize_counts_checks_and_up():
    rows = [
        make_row("https://a.com", "200", "True", "100"),
        make_row("https://a.com", "503", "False", "300"),
        make_row("https://b.com", "200", "True", "50"),
    ]
    stats, skipped = sitepulse.summarize_history(rows)

    assert stats["https://a.com"]["checks"] == 2
    assert stats["https://a.com"]["up"] == 1
    assert stats["https://b.com"]["checks"] == 1
    assert stats["https://b.com"]["up"] == 1
    assert skipped == 0


def test_summarize_only_times_checks_that_answered():
    rows = [
        make_row("https://a.com", "200", "True", "100"),
        make_row("https://a.com", "200", "True", "300"),
        # No status code = the site never answered (e.g. a 5-second timeout).
        # This should NOT be included in the response time total.
        make_row("https://a.com", "", "False", "5000"),
    ]
    stats, _ = sitepulse.summarize_history(rows)

    site = stats["https://a.com"]
    assert site["checks"] == 3
    assert site["answered"] == 2
    assert site["total_ms"] == 400


def test_summarize_accepts_excel_style_true_false():
    # Excel turns True/False into TRUE/FALSE when it saves a CSV file.
    rows = [
        make_row("https://a.com", "200", "TRUE", "100"),
        make_row("https://a.com", "500", "FALSE", "100"),
    ]
    stats, _ = sitepulse.summarize_history(rows)

    assert stats["https://a.com"]["up"] == 1


def test_summarize_skips_broken_rows():
    rows = [
        make_row("https://a.com", "200", "True", "100"),
        # response_ms isn't a number.
        make_row("https://a.com", "200", "True", "abc"),
        # A row with the is_up column missing (the value is None).
        {"url": "https://a.com", "status_code": "200", "is_up": None, "response_ms": "100"},
    ]
    stats, skipped = sitepulse.summarize_history(rows)

    assert stats["https://a.com"]["checks"] == 1
    assert skipped == 2


def test_summarize_keeps_sites_in_first_seen_order():
    rows = [
        make_row("https://b.com", "200", "True", "100"),
        make_row("https://a.com", "200", "True", "100"),
        make_row("https://b.com", "200", "True", "100"),
    ]
    stats, _ = sitepulse.summarize_history(rows)

    assert list(stats) == ["https://b.com", "https://a.com"]


def test_summarize_empty_history():
    stats, skipped = sitepulse.summarize_history([])

    assert stats == {}
    assert skipped == 0


# ---------- format_row ----------


def test_format_row_lines_up_columns():
    short = sitepulse.format_row("UP", "200", 50, "https://a.com", "", 20)
    long = sitepulse.format_row("DOWN", "-", 5000, "https://longer-name.com", "timed out", 23)

    # The URL starts at the same position on both lines.
    assert short.index("https://") == long.index("https://")


def test_format_row_has_no_spaces_at_the_end():
    line = sitepulse.format_row("UP", "200", 50, "https://a.com", "", 20)

    assert not line.endswith(" ")


# ---------- load_sites ----------
# tmp_path is a pytest feature: a brand-new empty folder for each test,
# so we can create test files without touching the real sites.json.


def test_load_sites_reads_the_list(tmp_path):
    sites_file = tmp_path / "sites.json"
    sites_file.write_text(json.dumps({"sites": ["https://a.com", "https://b.com"]}))

    assert sitepulse.load_sites(sites_file) == ["https://a.com", "https://b.com"]


def test_load_sites_missing_file_exits_cleanly(tmp_path):
    # load_sites calls sys.exit() with a friendly message, which raises
    # SystemExit. pytest.raises checks that it happens.
    with pytest.raises(SystemExit):
        sitepulse.load_sites(tmp_path / "does-not-exist.json")


def test_load_sites_broken_json_exits_cleanly(tmp_path):
    sites_file = tmp_path / "sites.json"
    sites_file.write_text('{"sites": [')

    with pytest.raises(SystemExit):
        sitepulse.load_sites(sites_file)


def test_load_sites_without_a_list_exits_cleanly(tmp_path):
    sites_file = tmp_path / "sites.json"
    sites_file.write_text(json.dumps({"sites": "https://a.com"}))

    with pytest.raises(SystemExit):
        sitepulse.load_sites(sites_file)


# ---------- save_history ----------
# monkeypatch.chdir moves the test into the temporary folder, so
# save_history writes a test history.csv there instead of the real one.


def test_save_history_writes_header_only_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    sitepulse.save_history([["2026-10-23 12:00:00", "https://a.com", 200, True, 100]])
    sitepulse.save_history([["2026-10-23 13:00:00", "https://a.com", "", False, 5000]])

    with open("history.csv", newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))

    assert rows[0] == sitepulse.HISTORY_COLUMNS
    assert len(rows) == 3  # 1 header + 2 results
    assert rows[2] == ["2026-10-23 13:00:00", "https://a.com", "", "False", "5000"]


# ---------- check_site with bad URLs ----------
# These URLs are rejected before any request is sent, so no internet is needed.


@pytest.mark.parametrize("bad_url", ["not a url", "htps://google.com", 123, None])
def test_check_site_bad_url_is_down(bad_url):
    # parametrize runs this test once for each bad_url in the list above.
    status, status_code, reason, _ = sitepulse.check_site(bad_url)

    assert status == "DOWN"
    assert status_code is None
    assert reason == "invalid URL"

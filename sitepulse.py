# SitePulse - a command-line tool that checks if websites are up.
# It reads a list of websites from sites.json, visits each one, and prints
# whether it is UP or DOWN, its status code, and how long it took to respond.
# If a site can't be reached, it is marked DOWN with a short reason and the
# program moves on to the next site instead of crashing.
# Every run's results are also added to history.csv so you can look back later.
#
# Usage:
#   py sitepulse.py            check every site in sites.json now
#   py sitepulse.py --report   show uptime % and average response time from history.csv

# "argparse" is built into Python. It reads options typed after the script
# name, like --report, and creates a --help message for free.
import argparse

# "csv" is built into Python. It reads and writes spreadsheet-style CSV files.
import csv

# "os" is built into Python. We use it to check whether history.csv exists yet.
import os

# "json" is built into Python. It turns JSON text into Python data
# (JSON lists become Python lists, JSON objects become dictionaries).
import json

# "sys" is built into Python. We use sys.exit() to stop the program cleanly
# with a friendly message when something is wrong with sites.json.
import sys

# "time" is built into Python. We use it to measure how long each request takes.
import time

# "datetime" is built into Python. We use it to stamp each run with the date and time.
from datetime import datetime

# "requests" is the outside library from requirements.txt.
# It lets Python visit web pages, like a browser does.
import requests

# The name of the file that holds our list of websites.
# Keeping it in a variable means we only have to change it in one place.
SITES_FILE = "sites.json"

# The file where results from every run are saved.
HISTORY_FILE = "history.csv"

# The column names for history.csv, in order.
HISTORY_COLUMNS = ["timestamp", "url", "status_code", "is_up", "response_ms"]

# How many seconds to wait for a site before giving up on it.
TIMEOUT_SECONDS = 5

# Every request includes a "User-Agent" that tells the site who is visiting.
# Some sites (like Wikipedia) block the default one that requests sends,
# so we give ours a clear name instead.
HEADERS = {"User-Agent": "SitePulse/1.0 (website uptime checker)"}


def load_sites(filename):
    """Open the JSON file and return the list of website URLs inside it.

    If the file is missing or broken, print a friendly message and stop.
    """
    try:
        # "with open(...)" opens the file and closes it automatically when done.
        # encoding="utf-8" avoids problems with special characters on Windows.
        with open(filename, encoding="utf-8") as file:
            # json.load reads the whole file and converts it into a dictionary,
            # e.g. {"sites": ["https://www.google.com", ...]}
            data = json.load(file)

        # We only want the list stored under the "sites" key.
        sites = data["sites"]

    # The file isn't in the folder we're running from.
    except FileNotFoundError:
        sys.exit(f"Error: could not find {filename}. Run SitePulse from the sitepulse folder.")

    # The file exists but isn't valid JSON (e.g. a missing comma or quote).
    except json.JSONDecodeError as error:
        sys.exit(f"Error: {filename} is not valid JSON ({error}).")

    # The JSON is valid but has no "sites" key, or isn't a dictionary at all.
    except (KeyError, TypeError):
        sys.exit(f'Error: {filename} must look like {{"sites": ["https://example.com"]}}.')

    # "sites" should be a list of URLs, not a single string or number.
    if not isinstance(sites, list):
        sys.exit(f'Error: "sites" in {filename} must be a list of URLs.')

    return sites


def check_site(url):
    """Visit one URL and return (status, status_code, reason, milliseconds).

    status is "UP" or "DOWN".
    status_code is the number the site sent back (e.g. 200), or None if it never answered.
    reason is a short explanation (e.g. "timed out") if it never answered, otherwise None.
    """
    # Start by assuming there's no status code and no problem.
    # The code below fills these in.
    status_code = None
    reason = None

    # perf_counter() is a very precise stopwatch. We note the time before
    # the request so we can work out how long it took afterwards.
    start = time.perf_counter()

    # "try" lets us catch errors instead of letting the program crash.
    # Each "except" below handles one kind of problem and gives it a reason.
    # Order matters: Python uses the first "except" that matches, so the
    # more specific errors come before the more general ones.
    try:
        # A URL must be text. If sites.json contains a number or null,
        # treat it as an invalid URL instead of crashing.
        if not isinstance(url, str):
            raise requests.exceptions.InvalidURL()

        # Send a GET request (the same kind a browser sends when you open a page).
        # timeout stops us waiting forever if the site doesn't respond.
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)

        # Status codes below 400 mean success (200 = OK, 301/302 = redirect).
        # 400 and above mean an error (404 = not found, 500 = server error).
        if response.status_code < 400:
            status = "UP"
        else:
            status = "DOWN"
        status_code = response.status_code

    # The site took longer than TIMEOUT_SECONDS to respond.
    except requests.exceptions.Timeout:
        status, reason = "DOWN", f"timed out after {TIMEOUT_SECONDS}s"

    # The URL itself is broken: missing "https://", a typo like "htps://",
    # or not a web address at all.
    except (
        requests.exceptions.MissingSchema,
        requests.exceptions.InvalidSchema,
        requests.exceptions.InvalidURL,
    ):
        status, reason = "DOWN", "invalid URL"

    # The site's security certificate is broken or expired.
    except requests.exceptions.SSLError:
        status, reason = "DOWN", "SSL certificate error"

    # We couldn't connect at all: the domain doesn't exist, the server
    # refused us, or there is no internet connection.
    except requests.exceptions.ConnectionError:
        status, reason = "DOWN", "could not connect (site not found or no internet)"

    # Any other requests problem (e.g. too many redirects).
    except requests.exceptions.RequestException:
        status, reason = "DOWN", "request failed"

    # A safety net for anything we didn't expect, so one bad site
    # can never stop the whole program.
    except Exception as error:
        status, reason = "DOWN", f"unexpected error ({type(error).__name__})"

    # Stop the stopwatch. The difference is in seconds, so * 1000 gives
    # milliseconds, and round() removes the decimal places.
    milliseconds = round((time.perf_counter() - start) * 1000)

    return status, status_code, reason, milliseconds


def save_history(rows):
    """Add this run's results to the end of history.csv.

    rows is a list of lists, one per site, in the same order as HISTORY_COLUMNS.
    """
    # If the file doesn't exist yet (or is empty), we need to write the
    # header row first. os.path.getsize gives the file size in bytes.
    is_new_file = not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0

    try:
        # "a" means append: add to the end of the file instead of replacing it.
        # newline="" stops Windows from adding blank lines between rows.
        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if is_new_file:
                writer.writerow(HISTORY_COLUMNS)
            writer.writerows(rows)

    # OSError covers problems saving the file, such as history.csv being
    # open in Excel (which locks it on Windows). The checks already ran,
    # so just warn instead of crashing.
    except OSError as error:
        print(f"\nWarning: could not save results to {HISTORY_FILE} ({error.strerror}).")
        print("If the file is open in Excel, close it and run SitePulse again.")


def format_row(status, code, time_ms, url, note, url_width):
    """Turn one row of the results table into a neatly lined-up line of text.

    :<n pads text on the right to n characters (left-aligned).
    :>n pads text on the left to n characters (right-aligned, good for numbers).
    """
    line = f"{status:<6}  {code:>4}  {time_ms:>9}  {url:<{url_width}}  {note}"

    # rstrip() removes spaces left at the end of the line when there's no note.
    return line.rstrip()


def run_checks():
    """Check every site in sites.json, print a table, and save to history.csv."""
    sites = load_sites(SITES_FILE)

    if not sites:
        print(f"No sites to check. Add some URLs to {SITES_FILE}.")
        return

    # len() tells us how many items are in the list.
    print(f"Checking {len(sites)} sites from {SITES_FILE}...\n")

    # One timestamp for the whole run, so all rows from this run share it
    # and are easy to group together. Example: 2026-10-23 14:05:00
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Collect a row for each site here, then save them all at the end.
    history_rows = []

    # Count how many sites are up, for the summary line at the end.
    up_count = 0

    # The URL column must be as wide as the longest URL so the NOTE column
    # lines up. str() handles anything in sites.json that isn't text.
    # max() picks the biggest number. The second line makes sure the column
    # is never narrower than its own title, "URL".
    url_width = max(len(str(url)) for url in sites)
    url_width = max(url_width, len("URL"))

    # Print the table header, then a line of dashes under each column title.
    print(format_row("STATUS", "CODE", "TIME (ms)", "URL", "NOTE", url_width))
    print(format_row("-" * 6, "-" * 4, "-" * 9, "-" * url_width, "-" * 4, url_width))

    # Loop through the list, one URL at a time. Each row prints as soon as
    # its site is checked, so you can watch the progress.
    for url in sites:
        status, status_code, reason, milliseconds = check_site(url)

        if status == "UP":
            up_count += 1

        # If the site never answered, show "-" instead of a code.
        if status_code is None:
            code_text = "-"
        else:
            code_text = str(status_code)

        # reason is None when there was no problem; show nothing in that case.
        note = reason or ""

        print(format_row(status, code_text, milliseconds, str(url), note, url_width))

        # If the site never answered, leave status_code blank in the CSV.
        if status_code is None:
            status_code = ""
        history_rows.append([timestamp, url, status_code, status == "UP", milliseconds])

    # The summary line, e.g. "3 of 4 sites are up."
    print(f"\n{up_count} of {len(sites)} sites are up.")

    save_history(history_rows)


def calculate_uptime(up, checks):
    """Return the percentage of checks that were UP, e.g. 3 out of 4 -> 75.0.

    Returns 0.0 if there were no checks, instead of dividing by zero.
    """
    if checks == 0:
        return 0.0
    return up / checks * 100


def summarize_history(rows):
    """Add up the results for each site from a list of history.csv rows.

    rows is a list of dictionaries, like the ones csv.DictReader gives.
    Returns (stats, skipped):
      stats is a dictionary where each key is a URL and each value is that
      site's totals: {"checks": ..., "up": ..., "answered": ..., "total_ms": ...}
      skipped is how many rows couldn't be understood.
    """
    # Dictionaries remember the order keys were added, so sites appear in
    # the order they were first checked.
    stats = {}

    # Count rows we couldn't understand (e.g. edited by hand by mistake).
    skipped = 0

    for row in rows:
        try:
            url = row["url"]
            # lower() means "True", "TRUE" and "true" all work.
            # Excel changes True to TRUE if you save the file from Excel.
            is_up = row["is_up"].strip().lower() == "true"
            response_ms = int(row["response_ms"])
            # An empty status_code means the site never answered.
            answered = row["status_code"].strip() != ""

        # KeyError: a column is missing. AttributeError: the row is too short
        # (the missing value is None). ValueError: response_ms isn't a number.
        except (KeyError, AttributeError, ValueError):
            skipped += 1
            continue

        # The first time we see a URL, start its totals at zero.
        if url not in stats:
            stats[url] = {"checks": 0, "up": 0, "answered": 0, "total_ms": 0}

        site = stats[url]
        site["checks"] += 1
        if is_up:
            site["up"] += 1

        # Only count response time when the site actually answered.
        # Failed checks would skew the average: a fake domain fails in
        # about 30 ms, while a timeout always takes 5000 ms.
        if answered:
            site["answered"] += 1
            site["total_ms"] += response_ms

    return stats, skipped


def show_report():
    """Read history.csv and print each site's uptime % and average response time.

    This doesn't visit any websites; it only looks at past results.
    """
    try:
        # encoding="utf-8-sig" also copes with the hidden marker Excel adds
        # to the start of a CSV file if you save it from Excel.
        with open(HISTORY_FILE, newline="", encoding="utf-8-sig") as file:
            # DictReader uses the header row, so each row becomes a dictionary
            # like {"url": "https://www.google.com", "is_up": "True", ...}
            # list() reads every row now, so the file can be closed straight away.
            rows = list(csv.DictReader(file))

    except FileNotFoundError:
        sys.exit(f"No {HISTORY_FILE} yet. Run 'py sitepulse.py' first to record some checks.")

    # OSError: the file can't be opened (e.g. no permission).
    # UnicodeDecodeError: the file isn't readable text.
    except (OSError, UnicodeDecodeError) as error:
        sys.exit(f"Error: could not read {HISTORY_FILE} ({error}).")

    # Add up the results for each site.
    stats, skipped = summarize_history(rows)

    if not stats:
        print(f"{HISTORY_FILE} has no results yet. Run 'py sitepulse.py' first.")
        return

    # Show the time range the report covers. Rows are added in time order,
    # so the first row is the oldest and the last row is the newest.
    # .get() gives "?" instead of crashing if the timestamp column is missing.
    first = rows[0].get("timestamp", "?")
    last = rows[-1].get("timestamp", "?")
    print(f"Report from {HISTORY_FILE} ({first} to {last})\n")

    # The URL comes last so the number columns can stay a fixed width.
    print(f"{'UPTIME':>7}  {'CHECKS':>6}  {'AVG (ms)':>8}  URL")
    print(f"{'-' * 7}  {'-' * 6}  {'-' * 8}  {'-' * 3}")

    for url, site in stats.items():
        uptime = calculate_uptime(site["up"], site["checks"])
        # :.1f shows one decimal place, e.g. 66.7
        uptime_text = f"{uptime:.1f}%"

        # If the site never answered, there's no average to show.
        if site["answered"] == 0:
            average_text = "-"
        else:
            average_text = str(round(site["total_ms"] / site["answered"]))

        print(f"{uptime_text:>7}  {site['checks']:>6}  {average_text:>8}  {url}")

    if skipped:
        print(f"\nSkipped {skipped} row(s) in {HISTORY_FILE} that couldn't be read.")


def main():
    """The starting point of the program: decide which mode to run."""
    # Describe the options this program accepts. argparse uses this to
    # read what was typed, and to print help for "py sitepulse.py --help".
    parser = argparse.ArgumentParser(description="Check whether websites are up.")
    parser.add_argument(
        "--report",
        # store_true means: if --report is typed, args.report is True, otherwise False.
        action="store_true",
        help=f"show uptime and average response time from {HISTORY_FILE} instead of running checks",
    )
    args = parser.parse_args()

    if args.report:
        show_report()
    else:
        run_checks()


# This line means "only run main() when this file is run directly"
# (e.g. "py sitepulse.py"), not when another file imports it.
if __name__ == "__main__":
    # Pressing Ctrl+C stops the program. Catch it so the user sees a short
    # message instead of a long error.
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")

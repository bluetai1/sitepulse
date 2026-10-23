# SitePulse - a command-line tool that checks if websites are up.
# It reads a list of websites from sites.json, visits each one, and prints
# whether it is UP or DOWN, its status code, and how long it took to respond.

# "json" is built into Python. It turns JSON text into Python data
# (JSON lists become Python lists, JSON objects become dictionaries).
import json

# "time" is built into Python. We use it to measure how long each request takes.
import time

# "requests" is the outside library from requirements.txt.
# It lets Python visit web pages, like a browser does.
import requests

# The name of the file that holds our list of websites.
# Keeping it in a variable means we only have to change it in one place.
SITES_FILE = "sites.json"

# How many seconds to wait for a site before giving up on it.
TIMEOUT_SECONDS = 5

# Every request includes a "User-Agent" that tells the site who is visiting.
# Some sites (like Wikipedia) block the default one that requests sends,
# so we give ours a clear name instead.
HEADERS = {"User-Agent": "SitePulse/1.0 (website uptime checker)"}


def load_sites(filename):
    """Open the JSON file and return the list of website URLs inside it."""
    # "with open(...)" opens the file and closes it automatically when done.
    # encoding="utf-8" avoids problems with special characters on Windows.
    with open(filename, encoding="utf-8") as file:
        # json.load reads the whole file and converts it into a dictionary,
        # e.g. {"sites": ["https://www.google.com", ...]}
        data = json.load(file)

    # We only want the list stored under the "sites" key.
    return data["sites"]


def check_site(url):
    """Visit one URL and return (status, status_code, milliseconds).

    status is "UP" or "DOWN". status_code is None if the site never answered.
    """
    # perf_counter() is a very precise stopwatch. We note the time before
    # the request so we can work out how long it took afterwards.
    start = time.perf_counter()

    # "try" lets us catch errors instead of letting the program crash.
    # Visiting a fake or broken site raises an error, so we need this.
    try:
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

    # RequestException covers every kind of requests error: the site doesn't
    # exist, there's no internet, the timeout ran out, and so on.
    except requests.exceptions.RequestException:
        status = "DOWN"
        status_code = None

    # Stop the stopwatch. The difference is in seconds, so * 1000 gives
    # milliseconds, and round() removes the decimal places.
    milliseconds = round((time.perf_counter() - start) * 1000)

    return status, status_code, milliseconds


def main():
    """The starting point of the program."""
    sites = load_sites(SITES_FILE)

    # len() tells us how many items are in the list.
    print(f"Checking {len(sites)} sites from {SITES_FILE}...\n")

    # Loop through the list, one URL at a time.
    for url in sites:
        status, status_code, milliseconds = check_site(url)

        # If the site never answered, there is no status code to show.
        if status_code is None:
            code_text = "no response"
        else:
            code_text = str(status_code)

        # :<4 pads the text to 4 characters wide so the columns line up.
        print(f"{status:<4}  {code_text:<11}  {milliseconds:>5} ms  {url}")


# This line means "only run main() when this file is run directly"
# (e.g. "py sitepulse.py"), not when another file imports it.
if __name__ == "__main__":
    main()

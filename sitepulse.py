# SitePulse - a command-line tool that checks if websites are up.
# It reads a list of websites from sites.json, visits each one, and prints
# whether it is UP or DOWN, its status code, and how long it took to respond.
# If a site can't be reached, it is marked DOWN with a short reason and the
# program moves on to the next site instead of crashing.

# "json" is built into Python. It turns JSON text into Python data
# (JSON lists become Python lists, JSON objects become dictionaries).
import json

# "sys" is built into Python. We use sys.exit() to stop the program cleanly
# with a friendly message when something is wrong with sites.json.
import sys

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
    """Visit one URL and return (status, detail, milliseconds).

    status is "UP" or "DOWN".
    detail is the status code (e.g. "200") if the site answered,
    or a short reason (e.g. "timed out") if it didn't.
    """
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
        detail = str(response.status_code)

    # The site took longer than TIMEOUT_SECONDS to respond.
    except requests.exceptions.Timeout:
        status, detail = "DOWN", f"timed out after {TIMEOUT_SECONDS}s"

    # The URL itself is broken: missing "https://", a typo like "htps://",
    # or not a web address at all.
    except (
        requests.exceptions.MissingSchema,
        requests.exceptions.InvalidSchema,
        requests.exceptions.InvalidURL,
    ):
        status, detail = "DOWN", "invalid URL"

    # The site's security certificate is broken or expired.
    except requests.exceptions.SSLError:
        status, detail = "DOWN", "SSL certificate error"

    # We couldn't connect at all: the domain doesn't exist, the server
    # refused us, or there is no internet connection.
    except requests.exceptions.ConnectionError:
        status, detail = "DOWN", "could not connect (site not found or no internet)"

    # Any other requests problem (e.g. too many redirects).
    except requests.exceptions.RequestException:
        status, detail = "DOWN", "request failed"

    # A safety net for anything we didn't expect, so one bad site
    # can never stop the whole program.
    except Exception as error:
        status, detail = "DOWN", f"unexpected error ({type(error).__name__})"

    # Stop the stopwatch. The difference is in seconds, so * 1000 gives
    # milliseconds, and round() removes the decimal places.
    milliseconds = round((time.perf_counter() - start) * 1000)

    return status, detail, milliseconds


def main():
    """The starting point of the program."""
    sites = load_sites(SITES_FILE)

    if not sites:
        print(f"No sites to check. Add some URLs to {SITES_FILE}.")
        return

    # len() tells us how many items are in the list.
    print(f"Checking {len(sites)} sites from {SITES_FILE}...\n")

    # Loop through the list, one URL at a time.
    for url in sites:
        status, detail, milliseconds = check_site(url)

        # :<4 pads the text to 4 characters wide so the columns line up.
        # :>5 lines the numbers up on the right.
        print(f"{status:<4}  {milliseconds:>5} ms  {url}  ({detail})")


# This line means "only run main() when this file is run directly"
# (e.g. "py sitepulse.py"), not when another file imports it.
if __name__ == "__main__":
    # Pressing Ctrl+C stops the program. Catch it so the user sees a short
    # message instead of a long error.
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")

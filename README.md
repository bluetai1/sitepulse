# SitePulse

SitePulse is a simple command-line tool that checks whether websites are up. It reads a list of sites from `sites.json`, sends a request to each one, and reports whether it responded, along with its status code and response time.

## Planned Features

- Read a list of websites from `sites.json`
- Check each site and show whether it is **UP** or **DOWN**
- Show the HTTP status code (for example, 200 or 404)
- Show how long each site took to respond
- Handle errors gracefully (bad addresses, timeouts, no internet) without crashing
- Print a summary at the end (for example, "3 up, 1 down")

## How to Run
install command, py sitepuls.py, and py sitepulse.py --report 

## Example output 
Report from history.csv (2026-10-23 04:07:33 to 2026-10-23 14:27:01)ers\ojota\Desktop\sitepulse>

 UPTIME  CHECKS  AVG (ms)  URL
-------  ------  --------  ---
  87.5%       8       625  https://www.google.com
  87.5%       8      1222  https://www.github.com
  87.5%       8       567  https://www.wikipedia.org
   0.0%       8         -  https://this-site-does-not-exist-sitepulse-test.com


## How I Used AI
I used the Claude Code extension in VS Code in Manual mode, building one feature at a time and testing the features as I go before commiting

## Problems I Ran Into
had problems connecting to the git and on my laptop it's py for python not python 
## What I'd Add Next
email alerts or a web dashboard
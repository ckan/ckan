from __future__ import with_statement
import os
import pytz
import subprocess

_cache_tz = None


def _get_localzone():
    pipe = subprocess.Popen(
        "systemsetup -gettimezone",
        shell=True,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    tzname = pipe.stdout.read().replace(b'Time Zone: ', b'').strip()

    if not tzname or tzname not in pytz.all_timezones_set:
        # link will be something like /usr/share/zoneinfo/America/Los_Angeles.
        link = os.readlink("/etc/localtime")
        tzname = link[link.rfind("zoneinfo/") + 9:]
    return pytz.timezone(tzname)


def get_localzone():
    """Get the computers configured local timezone, if any."""
    global _cache_tz
    if _cache_tz is None:
        _cache_tz = _get_localzone()
    return _cache_tz


def reload_localzone():
    """Reload the cached localzone. You need to call this if the timezone has changed."""
    global _cache_tz
    _cache_tz = _get_localzone()
    return _cache_tz

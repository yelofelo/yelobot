from datetime import datetime
from datetime import timedelta
import pytz
from timezonefinder import TimezoneFinder
import time
import calendar

TF = TimezoneFinder()

def tz_from_location(lat, lon):
    return TF.timezone_at(lng=float(lon), lat=float(lat))

def abbreviation_from_tz(tz):
    return pytz.timezone(tz).localize(datetime.now()).tzname()

def unix_at_time(timezone, month, day, year, hour, minute, second):
    tz = pytz.timezone(timezone)

    dt = datetime(year, month, day, hour, minute, second)
    localized = tz.localize(dt)

    return time.mktime(localized.astimezone(pytz.utc).timetuple())

def current_year_in_tz(timezone):
    tz = pytz.timezone(timezone)
    return datetime.now(tz).year

def current_month_in_tz(timezone):
    tz = pytz.timezone(timezone)
    return datetime.now(tz).month

def datetime_now_in_tz(timezone):
    tz = pytz.timezone(timezone)
    return datetime.now(tz)

def is_leap_year_in_tz(timezone):
    return calendar.isleap(current_year_in_tz(timezone))

def get_utc_offset(timezone) -> timedelta:
    offset = pytz.timezone(timezone).utcoffset(datetime.now(), is_dst=True)
    return offset.total_seconds() // 3600, (offset.total_seconds() % 3600) // 60

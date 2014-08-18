from datetime import datetime

def prettyDateNow():
    """
    Returns a good looking string for the local time.
    """
    return datetime.now().ctime()

def utcPrettyDateNow():
    """
    Returns a good looking string for utc time.
    """
    return datetime.utcnow().ctime()

class InvalidTimestampFormat(Exception):
    pass

def fromTimestamp(s):
    """
    Converts a string that is output from the timestamp function back to a
    datetime object

    Args:
        s (str): a ISO8601 formatted string.
            ex. 1912-06-23T101234Z"

    Note: we currently only support parsing strings that are generated from the
        timestamp function and have no intention in supporting the full standard.
    """
    try:
        date_part, time_part = s.split('T')
        hours, minutes, seconds = time_part[:2], time_part[2:4], time_part[4:6]
        year, month, day = date_part.split('-')
    except:
        raise InvalidTimestampFormat(s)

    return datetime(int(year), int(month), int(day), int(hours), int(minutes),
            int(seconds))

def timestamp(t=None):
    """
    The timestamp for ooni reports follows ISO 8601 in
    UTC time format.
    We do not inlcude ':' and include seconds.

    Example:

        if the current date is "10:12:34 AM, June 23 1912" (datetime(1912, 6,
            23, 10, 12, 34))

        the timestamp will be:

           "1912-06-23T101234Z"

    Args:
        t (datetime): a datetime object representing the
            time to be represented (*MUST* be expressed
            in UTC).

        If not specified will default to the current time
        in UTC.
    """
    if not t:
        t = datetime.utcnow()
    ISO8601 = "%Y-%m-%dT%H%M%SZ"
    return t.strftime(ISO8601)

def epochToTimestamp(seconds):
    return timestamp(datetime.utcfromtimestamp(seconds))

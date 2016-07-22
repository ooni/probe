from datetime import datetime

def prettyDateNow():
    """
    Returns a good looking string for the local time.
    """
    return datetime.now().ctime()

def prettyDateNowUTC():
    """
    Returns a good looking string for utc time.
    """
    return datetime.utcnow().ctime()

def timestampNowLongUTC():
    """
    Returns a timestamp in the format of %Y-%m-%d %H:%M:%S in Universal Time
    Coordinates.
    """
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def timestampNowISO8601UTC():
    """
    Returns a timestamp in the format of %Y-%m-%d %H:%M:%S in Universal Time
    Coordinates.
    """
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

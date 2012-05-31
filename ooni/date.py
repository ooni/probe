from datetime import datetime

def pretty_date():
    cur_time = datetime.utcnow()
    d_format = "%d %B %Y %H:%M:%S"
    pretty = cur_time.strftime(d_format)
    return pretty

def now():
    return datetime.utcnow()


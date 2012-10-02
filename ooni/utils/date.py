from ooni.lib.rfc3339 import rfc3339
from datetime import datetime

class odate(datetime):
    def __str__(self):
        return "%s" % rfc3339(self)

    def __repr__(self):
        return "%s" % rfc3339(self)

    def from_rfc(self, datestr):
        pass

def now():
    return odate.utcnow()

def pretty_date():
    cur_time = datetime.utcnow()
    d_format = "%d %B %Y %H:%M:%S"
    pretty = cur_time.strftime(d_format)
    return pretty


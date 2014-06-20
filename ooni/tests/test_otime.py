import unittest
from datetime import datetime
from ooni import otime

test_date = datetime(2002, 6, 26, 22, 45, 49)


class TestOtime(unittest.TestCase):
    def test_timestamp(self):
        self.assertEqual(otime.timestamp(test_date), "2002-06-26T224549Z")

    def test_fromTimestamp(self):
        time_stamp = otime.timestamp(test_date)
        self.assertEqual(test_date, otime.fromTimestamp(time_stamp))

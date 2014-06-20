from twisted.trial import unittest

from ooni.utils.trueheaders import TrueHeaders

dummy_headers_dict = {
    'Header1': ['Value1', 'Value2'],
    'Header2': ['ValueA', 'ValueB']
}

dummy_headers_dict2 = {
    'Header1': ['Value1', 'Value2'],
    'Header2': ['ValueA', 'ValueB'],
    'Header3': ['ValueA', 'ValueB'],
}

dummy_headers_dict3 = {
    'Header1': ['Value1', 'Value2'],
    'Header2': ['ValueA', 'ValueB'],
    'Header4': ['ValueA', 'ValueB'],
}


class TestTrueHeaders(unittest.TestCase):
    def test_names_match(self):
        th = TrueHeaders(dummy_headers_dict)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict)), set())

    def test_names_not_match(self):
        th = TrueHeaders(dummy_headers_dict)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict2)), set(['Header3']))

        th = TrueHeaders(dummy_headers_dict3)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict2)), set(['Header3', 'Header4']))

    def test_names_match_expect_ignore(self):
        th = TrueHeaders(dummy_headers_dict)
        self.assertEqual(th.getDiff(TrueHeaders(dummy_headers_dict2), ignore=['Header3']), set())





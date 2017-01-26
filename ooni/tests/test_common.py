from twisted.trial import unittest
from ooni.common.http_utils import META_CHARSET_REGEXP
from ooni.common.ip_utils import is_public_ipv4_address, is_private_ipv4_address

class TestHTTPUtils(unittest.TestCase):
    def test_charset_detection(self):
        no_charset_html = """
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
        <title>Foo</title>
"""
        with_charset_html = no_charset_html + '\n<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">'
        with_empty_charset = no_charset_html + '\n<meta http-equiv="Content-Type" content="text/html; charset=">'
        with_two_charsets = no_charset_html + '\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8;charset=utf-8">'
        self.assertEqual(META_CHARSET_REGEXP.search(no_charset_html), None)
        self.assertEqual(META_CHARSET_REGEXP.search(with_charset_html).group(1), 'iso-8859-1')
        self.assertEqual(META_CHARSET_REGEXP.search(
            with_two_charsets).group(1), 'UTF-8')
        self.assertEqual(META_CHARSET_REGEXP.search(with_empty_charset), None)

class TestIPUtils(unittest.TestCase):
    def test_is_public_ipv4(self):
        self.assertTrue(is_public_ipv4_address('8.8.8.8'))
        self.assertFalse(is_public_ipv4_address('example.com'))
        self.assertFalse(is_public_ipv4_address('127.0.0.1'))
        self.assertFalse(is_public_ipv4_address('192.168.1.1'))

    def test_is_private_ipv4(self):
        self.assertFalse(is_private_ipv4_address('8.8.8.8'))
        self.assertFalse(is_private_ipv4_address('example.com'))
        self.assertTrue(is_private_ipv4_address('127.0.0.1'))
        self.assertTrue(is_private_ipv4_address('192.168.2.2'))

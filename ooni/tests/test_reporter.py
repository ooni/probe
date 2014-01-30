import yaml
import time

from twisted.trial import unittest

from ooni.reporter import YAMLReporter

class MockTest(object):
    _start_time = time.time()
    report = {'report_content': 'ham'}
    input = 'spam'

class TestYAMLReporter(unittest.TestCase):
    def setUp(self):
        pass

    def test_write_report(self):
        test_details = {
                'test_name': 'spam',
                'test_version': '1.0'
        }
        test = MockTest()

        y_reporter = YAMLReporter(test_details)
        y_reporter.createReport()
        y_reporter.testDone(test, 'spam')
        with open(y_reporter.report_path) as f:
            report_entries = yaml.safe_load_all(f)
            # Check for keys in header
            entry = report_entries.next()
            assert all(x in entry for x in ['test_name', 'test_version'])

            entry = report_entries.next()
            # Check for first entry of report
            assert all(x in entry \
                       for x in ['report_content', 'input', \
                                 'test_name', 'test_started', \
                                 'test_runtime'])


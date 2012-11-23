from twisted.trial import unittest


from ooni.inputunit import InputUnit
from ooni.nettest import NetTestCase
from ooni.reporter import OReporter

from ooni.runner import loadTestsAndOptions, runTestCasesWithInputUnit


class DummyTestCase(NetTestCase):
    def test_a(self):
        self.report['bar'] = 'bar'
    def test_b(self):
        self.report['foo'] = 'foo'

class DummyTestCasePP(DummyTestCase):
    def postProcessor(self, report):
        self.report['antani'] = 'sblinda'

class DummyReporter(OReporter):
    dummy_report = []
    def createReport(self, options):
        pass

    def writeReportEntry(self, entry):
        self.dummy_report.append(entry)

class TestRunner(unittest.TestCase):
    def test_load_test_and_options(self):
        input_unit = InputUnit([0,1,2,3,4])
        cmd_line_options = {}
        test_cases, options = loadTestsAndOptions([DummyTestCase],
                cmd_line_options)
        self.assertEqual(test_cases[0][1], 'test_b')
        self.assertEqual(test_cases[1][1], 'test_a')

    def test_run_testcase_with_input_unit(self):
        oreporter = DummyReporter()
        oreporter.dummy_report = []
        def done(result):
            report = oreporter.dummy_report
            self.assertEqual(len(report), 5*2)
            for idx, entry in enumerate(oreporter.dummy_report):
                if idx % 2 == 0:
                    self.assertEqual(entry['report']['foo'], 'foo')
                else:
                    self.assertEqual(entry['report']['bar'], 'bar')

        input_unit = InputUnit([0,1,2,3,4])
        cmd_line_options = {'collector': None}

        test_cases, options = loadTestsAndOptions([DummyTestCase],
                cmd_line_options)

        d = runTestCasesWithInputUnit(test_cases, input_unit, oreporter)
        d.addBoth(done)
        return d

    def test_with_post_processing(self):
        oreporter = DummyReporter()
        oreporter.dummy_report = []
        def done(result):
            report = oreporter.dummy_report
            self.assertEqual(len(report), 3)
            for entry in report:
                if entry['test_name'] == 'summary':
                    self.assertEqual(entry['report'], {'antani': 'sblinda'})

        input_unit = InputUnit([None])
        cmd_line_options = {'collector': None}

        test_cases, options = loadTestsAndOptions([DummyTestCasePP],
                cmd_line_options)

        d = runTestCasesWithInputUnit(test_cases, input_unit, oreporter)
        d.addBoth(done)
        return d

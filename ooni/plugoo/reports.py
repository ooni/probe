from __future__ import with_statement

import os
import yaml

import itertools
from ooni.utils import log, date, net

class Report:
    """This is the ooni-probe reporting mechanism. It allows
    reporting to multiple destinations and file formats.

    :scp the string of <host>:<port> of an ssh server

    :yaml the filename of a the yaml file to write

    :file the filename of a simple txt file to write

    :tcp the <host>:<port> of a TCP server that will just listen for
         inbound connection and accept a stream of data (think of it
         as a `nc -l -p <port> > filename.txt`)
    """
    def __init__(self, testname=None, file="report.log",
                 scp=None,
                 tcp=None):

        self.testname = testname
        self.file = file
        self.tcp = tcp
        self.scp = scp
        #self.config = ooni.config.report

        #if self.config.timestamp:
        #    tmp = self.file.split('.')
        #    self.file = '.'.join(tmp[:-1]) + "-" + \
        #                datetime.now().isoformat('-') + '.' + \
        #                tmp[-1]
        #    print self.file

        self.scp = None
        self.write_header()

    def write_header(self):
        pretty_date = date.pretty_date()
        header = "# OONI Probe Report for Test %s\n" % self.testname
        header += "# %s\n\n" % pretty_date
        self._write_to_report(header)
        # XXX replace this with something proper
        address = net.getClientAddress()
        test_details = {'start_time': str(date.now()),
                        'asn': address['asn'],
                        'test_name': self.testname,
                        'addr': address['ip']}
        self(test_details)

    def _write_to_report(self, dump):
        reports = []

        if self.file:
            reports.append("file")

        if self.tcp:
            reports.append("tcp")

        if self.scp:
            reports.append("scp")

        #XXX make this non blocking
        for report in reports:
            self.send_report(dump, report)

    def __call__(self, data):
        """
        This should be invoked every time you wish to write some
        data to the reporting system
        """
        dump = yaml.dump([data])
        self._write_to_report(dump)

    def file_report(self, data):
        """
        This reports to a file in YAML format
        """
        with open(self.file, 'a+') as f:
            f.write(data)

    def send_report(self, data, type):
        """
        This sends the report using the
        specified type.
        """
        #print "Reporting %s to %s" % (data, type)
        log.msg("Reporting to %s" % type)
        getattr(self, type+"_report").__call__(data)

class NewReport(object):
    filename = 'report.log'
    startTime = None
    endTime = None
    testName = None
    ipAddr = None
    asnAddr = None

    def _open():
        self.fp = open(self.filename, 'a+')

    @property
    def header():
        pretty_date = date.pretty_date()
        report_header = "# OONI Probe Report for Test %s\n" % self.testName
        report_header += "# %s\n\n" % pretty_date
        test_details = {'start_time': self.startTime,
                        'asn': asnAddr,
                        'test_name': self.testName,
                        'addr': ipAddr}
        report_header += yaml.dump([test_details])
        return report_header

    def create():
        """
        Create a new report by writing it's header.
        """
        self.fp = open(self.filename, 'w+')
        self.fp.write(self.header)

    def exists():
        """
        Returns False if the file does not exists.
        """
        return os.path.exists(self.filename)

    def write(data):
        """
        Write a report to the file.

        :data: python data structure to be written to report.
        """
        if not self.exists():
            self.create()
        else:
            self._open()
        yaml_encoded_data = yaml.dump([data])
        self.fp.write(yaml_encoded_data)
        self.fp.close()


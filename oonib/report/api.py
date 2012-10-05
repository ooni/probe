"""
/report/do

/report/pcap

This is the async pcap reporting system. It requires the client to have created a report already, but can work independently from test progress.

"""
import random
import string
from twisted.internet import reactor, defer
from cyclone import web

from oonib.report.db import models
backend_version = '0.0.1'

def generateReportID():
    size = 100
    report_id = ''.join(random.choice(string.ascii_letters) for x in range(size))
    return report_id

@defer.inlineCallbacks
def newReport(software_name, software_version, test_name, test_version,
               progress, content):

    report_id = generateReportID()

    new_report = models.Report()

    new_report.report_id = unicode(report_id)

    new_report.software_name = unicode(software_name)
    new_report.software_version = unicode(software_version)
    new_report.test_name = unicode(test_name)
    new_report.test_version = unicode(test_version)
    new_report.progress = unicode(progress)
    new_report.content = unicode(content)

    print "Software Name: %s" % software_name
    print "Software Version: %s" % software_version
    print "Test Name: %s" % test_name
    print "Test Version: %s" % test_version
    print "Progress: %s" % progress
    print "Content: %s" % content

    yield new_report.save()

    defer.returnValue({'backend_version': backend_version, 'report_id':
                        report_id})

def updateReport(report_id, content):
    print "Report ID: %s" % report_id
    print "Content: %s" % content

    return {'backend_version': backend_version, 'report_id': report_id}

class NewReportHandler(web.RequestHandler):
    """
    Responsible for creating and updating reports.
    """

    @web.asynchronous
    @defer.inlineCallbacks
    def get(self):
        """
        Creates a new report with the input

        * Request

          {'software_name': 'XXX',
           'software_version': 'XXX',
           'test_name': 'XXX',
           'test_version': 'XXX',
           'progress': 'XXX',
           'content': 'XXX'
           }

          Optional:
            'test_helper': 'XXX'
            'client_ip': 'XXX'

        * Response

          {'backend_version': 'XXX', 'report_id': 'XXX'}

        """
        # This is the list of supported arguments
        arguments = ['software_name', 'software_version',
                     'test_name','test_version',
                     'progress', 'content']
        report = {}
        for arg in arguments:
            if len(self.get_arguments(arg)) == 0:
                raise web.HTTPError(400, "%s not specified as argument of POST"
                        % arg)
            report[arg] = self.get_argument(arg)

        try:
            test_helper = self.get_argument('test_helper')


        except web.HTTPError:
            pass

        new_report = yield newReport(**report)

        self.write(new_report)
        self.finish()

    def put(self):
        """
        Update an already existing report.

          {'report_id': 'XXX',
           'content': 'XXX'
          }
        """
        pass

class PCAPReportHandler(web.RequestHandler):
    def get(self):
        pass

    def post(self):
        pass

spec = [(r"/report/new", NewReportHandler),
        (r"/report/pcap", PCAPReportHandler)]

reportingBackend = web.Application(spec)


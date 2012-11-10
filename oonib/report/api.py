"""
/report/do

/report/pcap

This is the async pcap reporting system. It requires the client to have created a report already, but can work independently from test progress.

"""
import random
import string
import json

from twisted.internet import reactor, defer

from cyclone import web

from oonib.report import models

backend_version = '0.0.1'

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
    def post(self):
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
        parsed_request = json.loads(self.request.body)

        # XXX here we should validate and sanitize the request

        report_data = parsed_request

        new_report = models.Report()

        print "Got %s as request" % parsed_request
        result = yield new_report.new(report_data)

        self.write(result)
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

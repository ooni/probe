"""
/new

/pcap

This is the async pcap reporting system. It requires the client to have created a report already, but can work independently from test progress.

"""
import random
import string
import json
import re
import os

from twisted.internet import reactor, defer

from cyclone import web

from ooni.utils import randomStr, otime
from oonib import models, config
from oonib.report import file_collector

def parseUpdateReportRequest(request):
    #db_report_id_regexp = re.compile("[a-zA-Z0-9]+$")

    # this is the regexp for the reports that include the timestamp
    report_id_regexp = re.compile("[a-zA-Z0-9_-]+$")

    # XXX here we are actually parsing a json object that could be quite big.
    # If we want this to scale properly we only want to look at the test_id
    # field.
    # We are also keeping in memory multiple copies of the same object. A lot
    # of optimization can be done.
    parsed_request = json.loads(request)
    try:
        report_id = parsed_request['report_id']
    except KeyError:
        raise MissingField('report_id')

    if not re.match(report_id_regexp, report_id):
        raise InvalidRequestField('report_id')

    return parsed_request


class NewReportHandlerDB(web.RequestHandler):
    """
    Responsible for creating and updating reports via database.
    XXX this is not yet fully implemented.
    """

    @web.asynchronous
    @defer.inlineCallbacks
    def post(self):
        """
        Creates a new report with the input to the database.
        XXX this is not yet implemented.

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
        report_data = json.loads(self.request.body)
        new_report = models.Report()
        log.debug("Got this request %s" % report_data)
        result = yield new_report.new(report_data)
        self.write(result)
        self.finish()

    def put(self):
        """
        Update an already existing report with the database.

        XXX this is not yet implemented.

          {'report_id': 'XXX',
           'content': 'XXX'
          }
        """
        pass


reportingBackendAPI = [
    (r"/report", file_collector.NewReportHandlerFile),
    (r"/pcap", file_collector.PCAPReportHandler)
]

reportingBackend = web.Application(reportingBackendAPI, debug=True)

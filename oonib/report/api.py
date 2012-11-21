"""
/report/do

/report/pcap

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

backend_version = '0.0.1'

def generateReportID():
    return otime.timestamp() + '_' + randomStr(20)

class MissingField(Exception):
    pass

class InvalidRequestField(Exception):
    pass

def parseNewReportRequest(request):
    """
    Here we parse a new report request.
    """
    version_string = re.compile("[0-9A-Za-z_\-\.]+$")
    name = re.compile("[a-zA-Z0-9_\- ]+$")
    expected_request = {'software_name': name,
     'software_version': version_string,
     'test_name': name,
     'test_version': version_string,
     'progress': re.compile("[0-9]+$")
    }
    parsed_request = json.loads(request)
    for k, regexp in expected_request.items():
        try:
            value_to_check = parsed_request[k]
        except KeyError:
            raise MissingField(k)
        print "Matching %s with %s | %s" % (regexp, value_to_check, k)
        if re.match(regexp, str(value_to_check)):
            continue
        else:
            raise InvalidRequestField(k)
    return parsed_request

def parseUpdateReportRequest(request):
    # XXX this and the function above can probably be refactored into something
    # more compact. There is quite a bit of code duplication going on here.

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

class NewReportHandlerFile(web.RequestHandler):
    """
    Responsible for creating and updating reports by writing to flat file.
    """
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
        # XXX here we should validate and sanitize the request
        try:
            report_data = parseNewReportRequest(self.request.body)
        except InvalidRequestField, e:
            raise web.HTTPError(400, "Invalid Request Field %s" % e)
        except MissingField, e:
            raise web.HTTPError(400, "Missing Request Field %s" % e)

        print "Parsed this data %s" % report_data
        software_name = report_data['software_name']
        software_version = report_data['software_version']
        test_name = report_data['test_name']
        test_version = report_data['test_version']
        content = report_data['content']

        report_id = generateReportID()

        #report_filename = '_'.join((report_id,
        #    report_data['software_name'],
        #    report_data['software_version'],
        #    report_data['test_name'],
        #    report_data['test_version']))

        # The report filename contains the timestamp of the report plus a
        # random nonce
        report_filename = os.path.join(config.main.report_dir, report_id)
        report_filename += '.yamloo'

        response = {'backend_version': backend_version, 
                'report_id': report_id
                }

        fp = open(report_filename, 'w+')
        fp.write(report_data['content'])
        fp.close()
        self.write(response)

    def put(self):
        """
        Update an already existing report.

          {'report_id': 'XXX',
           'content': 'XXX'
          }
        """
        parsed_request = parseUpdateReportRequest(self.request.body)
        report_id = parsed_request['report_id']
        print "Got this request %s" % parsed_request

        report_filename = os.path.join(config.main.report_dir, report_id)
        report_filename += '.yamloo'
        try:
            with open(report_filename, 'a+') as f: 
                # XXX this could be quite big. We should probably use the
                # twisted.internet.fdesc module
                print parsed_request['content']
                f.write(parsed_request['content'])
        except IOError as e:
            web.HTTPError(404, "Report not found")

class NewReportHandlerDB(web.RequestHandler):
    """
    Responsible for creating and updating reports via database.
    XXX this is not yet fully implemented.
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

reportingBackendAPI = [(r"/report/new", NewReportHandlerFile),
    (r"/report/pcap", PCAPReportHandler)
]

reportingBackend = web.Application(reportingBackendAPI, debug=True)

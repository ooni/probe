import random
import string
import json
import re
import os

from twisted.internet import fdesc

from cyclone import web

from ooni.utils import randomStr
from ooni import otime

from oonib.report import MissingField, InvalidRequestField

from oonib import config

def parseUpdateReportRequest(request):
    #db_report_id_regexp = re.compile("[a-zA-Z0-9]+$")

    # this is the regexp for the reports that include the timestamp
    report_id_regexp = re.compile("[a-zA-Z0-9_\-]+$")

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



def parseNewReportRequest(request):
    """
    Here we parse a new report request.
    """
    version_string = re.compile("[0-9A-Za-z_\-\.]+$")
    name = re.compile("[a-zA-Z0-9_\- ]+$")
    probe_asn = re.compile("AS[0-9]+$")

    expected_request = {
     'software_name': name,
     'software_version': version_string,
     'test_name': name,
     'test_version': version_string,
     'probe_asn': probe_asn
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
           'probe_asn': 'XXX'
           'content': 'XXX'
           }

          Optional:
            'test_helper': 'XXX'
            'client_ip': 'XXX'

          (not implemented, nor in client, nor in backend)
          The idea behind these two fields is that it would be interesting to
          also collect how the request was observed from the collectors point
          of view.

          We use as a unique key the client_ip address and a time window. We
          then need to tell the test_helper that is selected the client_ip
          address and tell it to expect a connection from a probe in that time
          window.

          Once the test_helper sees a connection from that client_ip it will
          store for the testing session the data that it receives.
          When the probe completes the report (or the time window is over) the
          final report will include also the data collected from the
          collectors view point.

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
        probe_asn = report_data['probe_asn']
        content = report_data['content']

        if not probe_asn:
            probe_asn = "AS0"

        report_id = otime.timestamp() + '_' \
                + probe_asn + '_' \
                + randomStr(50)

        # The report filename contains the timestamp of the report plus a
        # random nonce
        report_filename = os.path.join(config.main.report_dir, report_id)

        response = {'backend_version': config.backend_version,
                'report_id': report_id
        }

        self.writeToReport(report_filename,
                report_data['content'])

        self.write(response)

    def writeToReport(self, report_filename, data):
        with open(report_filename, 'w+') as fd:
            fdesc.setNonBlocking(fd.fileno())
            fdesc.writeToFD(fd.fileno(), data)

    def put(self):
        """
        Update an already existing report.

          {
           'report_id': 'XXX',
           'content': 'XXX'
          }
        """
        parsed_request = parseUpdateReportRequest(self.request.body)

        report_id = parsed_request['report_id']

        print "Got this request %s" % parsed_request
        report_filename = os.path.join(config.main.report_dir,
                report_id)

        self.updateReport(report_filename, parsed_request['content'])

    def updateReport(self, report_filename, data):
        try:
            with open(report_filename, 'a+') as fd:
                fdesc.setNonBlocking(fd.fileno())
                fdesc.writeToFD(fd.fileno(), data)
        except IOError as e:
            web.HTTPError(404, "Report not found")

class PCAPReportHandler(web.RequestHandler):
    def get(self):
        pass

    def post(self):
        pass

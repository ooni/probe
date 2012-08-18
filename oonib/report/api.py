"""
/report/do

/report/pcap

This is the async pcap reporting system. It requires the client to have created a report already, but can work independently from test progress.

"""
import random
import strings
from twisted.internet import reactor
from cyclone import web
backend_version = '0.0.1'

def generateReportID():
    size = 100
    id = ''.join(random.choice(strings.ascii_letters) for x in range(size))
    return id

def newReport(software_name, software_version, test_name, test_version,
               progress, content):
    print "Software Name: %s" % software_name
    print "Software Version: %s" % software_version
    print "Test Name: %s" % test_name
    print "Test Version: %s" % test_version
    print "Progress: %s" % progress
    print "Content: %s" % content
    reportId = generateReportID()
    return {'backend_version': backend_version, 'report_id': reportID}

def updateReport(report_id, content):
    print "Report ID: %s" % report_id
    print "Content: %s" % content
    return {'backend_version': '0.1', 'report_id': 'FOOBAR'}

class DoReportHandler(web.RequestHandler):
    """
    Responsible for creating and updating reports.
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

        * Response

          {'backend_version': 'XXX', 'report_id': 'XXX'}

        """
        # This is the list of supported arguments
        arguments = ['software_name', 'software_version',
                     'test_name','test_version',
                     'progress', 'content']
        report = {}
        error = None
        for arg in arguments:
            if len(self.get_arguments(arg)) == 0:
                print "No %s specified" % arg
                error = arg
                break
            report[arg] = self.get_argument(arg)
        if not error:
            self.write(newReport(**report))

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

handlers = [(r"/report/do", DoReportHandler),
            (r"/report/pcap", PCAPReportHandler)]

reporting = web.Application(handlers)
reactor.listenTCP(8888, reporting, interface="127.0.0.1")
print "starting bullshit"
reactor.run()


import os
import re
import copy
import json
import types

from twisted.python import usage
from cyclone import web, escape

from ooni.reporter import YAMLReporter, OONIBReporter
from ooni import errors
from ooni.nettest import NetTestLoader, MissingRequiredOption
from ooni.settings import config

class InvalidInputFilename(Exception):
    pass

class FilenameExists(Exception):
    pass

class ORequestHandler(web.RequestHandler):
    serialize_lists = True

    def write(self, chunk):
        """
        XXX This is a patch that can be removed once
        https://github.com/fiorix/cyclone/pull/92 makes it into a release.
        """
        if isinstance(chunk, types.ListType):
            chunk = escape.json_encode(chunk)
            self.set_header("Content-Type", "application/json")
        web.RequestHandler.write(self, chunk)

class Status(ORequestHandler):
    def get(self):
        result = {'active_tests': oonidApplication.director.activeNetTests}
        self.write(result)

def list_inputs():
    input_list = []
    for filename in os.listdir(config.inputs_directory):
        input_list.append({'filename': filename})
    return input_list

class Inputs(ORequestHandler):
    def get(self):
        input_list = list_inputs()
        self.write(input_list)

    def post(self):
        filename = self.get_argument("fullname", None)
        if not filename or not re.match('(\w.*\.\w.*).*', filename):
            raise InvalidInputFilename

        if os.path.exists(filename):
            raise FilenameExists

        input_file = self.request.files.get("input_file")
        content_type = input_file["content_type"]
        body = input_file["body"]

        fn = os.path.join(config.inputs_directory, filename)
        with open(os.path.abspath(fn), "w") as fp:
            fp.write(body)

class ListTests(ORequestHandler):
    def get(self):
        test_list = copy.deepcopy(oonidApplication.director.netTests)
        for test_id in test_list.keys():
            test_list[test_id].pop('path')
        self.write(test_list)

def get_net_test_loader(test_options, test_file):
    options = []
    for k, v in test_options.items():
        options.append('--'+k)
        options.append(v)

    net_test_loader = NetTestLoader(options,
            test_file=test_file)
    return net_test_loader

def get_reporters(net_test_loader):
    test_details = net_test_loader.testDetails
    yaml_reporter = YAMLReporter(test_details, config.reports_directory)
    #oonib_reporter = OONIBReporter(test_details, collector)
    return [yaml_reporter]

class StartTest(ORequestHandler):
    def post(self, test_name):
        """
        Starts a test with the specified options.
        """
        test_file = oonidApplication.director.netTests[test_name]['path']
        test_options = json.loads(self.request.body)
        net_test_loader = get_net_test_loader(test_options, test_file)
        try:
            net_test_loader.checkOptions()
            oonidApplication.director.startNetTest(net_test_loader,
                                                   get_reporters(net_test_loader))
        except MissingRequiredOption, option_name:
            self.write({'error':
                        'Missing required option: "%s"' % option_name})
        except usage.UsageError, e:
            self.write({'error':
                        'Error in parsing options'})
        except errors.InsufficientPrivileges:
            self.write({'error':
                        'Insufficient priviledges'})

class StopTest(ORequestHandler):
    def delete(self, test_name):
        pass

def get_test_results(test_id):
    test_results = []
    for test_result in os.listdir(config.reports_directory):
        if test_result.startswith('report-'+test_id):
            with open(os.path.join(config.reports_directory, test_result)) as f:
                test_content = ''.join(f.readlines())
            test_results.append({'name': test_result,
                                 'content': test_content})
    return test_results

class TestStatus(ORequestHandler):
    def get(self, test_id):
        try:
            test = copy.deepcopy(oonidApplication.director.netTests[test_id])
            test.pop('path')
            test['results'] = get_test_results(test_id)
            self.write(test)
        except KeyError:
            self.write({'error':
                        'Test with such ID not found!'})

config.read_config_file()
oonidAPI = [
    (r"/status", Status),
    (r"/inputs", Inputs),
    (r"/test", ListTests),
    (r"/test/(.*)/start", StartTest),
    (r"/test/(.*)/stop", StopTest),
    (r"/test/(.*)", TestStatus),
    (r"/(.*)", web.StaticFileHandler,
        {"path": os.path.join(config.data_directory, 'ui', 'app'),
         "default_filename": "index.html"})
]

oonidApplication = web.Application(oonidAPI, debug=True)


import os
import re
import json
import types

from cyclone import web, escape

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
        self.write(oonidApplication.director.netTests)

class StartTest(ORequestHandler):
    def post(self, test_name):
        """
        Starts a test with the specified options.
        """
        json.decode(self.request.body)

class StopTest(ORequestHandler):
    def delete(self, test_name):
        pass

class TestStatus(ORequestHandler):
    def get(self, test_id):
        pass

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


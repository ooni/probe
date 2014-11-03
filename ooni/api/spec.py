import os
import re
import copy
import json
import types
import tempfile
import functools

from twisted.python import usage
from cyclone import web, escape

from ooni.reporter import YAMLReporter, OONIBReporter, collector_supported
from ooni import errors
from ooni.nettest import NetTestLoader
from ooni.settings import config

class InvalidInputFilename(Exception):
    pass

class FilenameExists(Exception):
    pass

def check_xsrf(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kw):
        xsrf_header = self.request.headers.get("X-XSRF-TOKEN")
        if self.xsrf_token != xsrf_header:
            raise web.HTTPError(403, "Invalid XSRF token.")
        return method(self, *args, **kw)
    return wrapper

class ORequestHandler(web.RequestHandler):
    serialize_lists = True
    xsrf_cookie_name = "XSRF-TOKEN"

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
    @check_xsrf
    def get(self):
        result = {'active_tests': oonidApplication.director.activeNetTests}
        self.write(result)

def list_inputs():
    input_list = []
    for filename in os.listdir(config.inputs_directory):
        input_list.append({'filename': filename})
    return input_list

class Inputs(ORequestHandler):
    """
    This handler is responsible for listing and adding new inputs.
    """

    @check_xsrf
    def get(self):
        """
        Obtain the list of currently installed inputs. Inputs are stored inside
        of $OONI_HOME/inputs/.
        """
        input_list = list_inputs()
        self.write(input_list)

    @check_xsrf
    def post(self):
        """
        Add a new input to the currently installed inputs.
        """
        input_file = self.request.files.get("file")[0]
        filename = input_file['filename']

        if not filename or not re.match('(\w.*\.\w.*).*', filename):
            raise InvalidInputFilename

        if os.path.exists(filename):
            raise FilenameExists

        content_type = input_file["content_type"]
        body = input_file["body"]

        fn = os.path.join(config.inputs_directory, filename)
        with open(os.path.abspath(fn), "w") as fp:
            fp.write(body)

class ListTests(ORequestHandler):

    @check_xsrf
    def get(self):
        test_list = copy.deepcopy(oonidApplication.director.netTests)
        for test_id in test_list.keys():
            test_list[test_id].pop('path')
        self.write(test_list)

def get_net_test_loader(test_options, test_file):
    """
    Args:
        test_options: (dict) containing as keys the option names.

        test_file: (string) the path to the test_file to be run.
    Returns:
        an instance of :class:`ooni.nettest.NetTestLoader` with the specified
        test_file and the specified options.
        """
    options = []
    for k, v in test_options.items():
        options.append('--'+k)
        options.append(v)

    net_test_loader = NetTestLoader(options,
            test_file=test_file)
    return net_test_loader

def get_reporters(net_test_loader):
    """
    Determines which reports are able to run and returns an instance of them.

    We always report to flat file via the :class:`ooni.reporters.YAMLReporter`
    and the :class:`ooni.reporters.OONIBReporter`.

    The later will be used only if we determine that Tor is running.

    Returns:
        a list of reporter instances
    """
    test_details = net_test_loader.testDetails
    reporters = []
    yaml_reporter = YAMLReporter(test_details, config.reports_directory)
    reporters.append(yaml_reporter)

    if config.reports.collector and collector_supported(config.reports.collector):
        oonib_reporter = OONIBReporter(test_details, config.reports.collector)
        reporters.append(oonib_reporter)
    return reporters

def write_temporary_input(content):
    """
    Creates a temporary file for the given content.

    Returns:
        the path to the temporary file.
    """
    fd, path = tempfile.mkstemp()
    with open(path, 'w') as f:
        f.write(content)
        f.close()
    print "This is the path %s" % path
    return fd, path

class StartTest(ORequestHandler):

    @check_xsrf
    def post(self, test_name):
        """
        Starts a test with the specified options.
        """
        test_file = oonidApplication.director.netTests[test_name]['path']
        test_options = json.loads(self.request.body)
        tmp_files = []
        if ('manual_input' in test_options):
            for option, content in test_options['manual_input'].items():
                fd, path = write_temporary_input(content)
                test_options[option] = path
                tmp_files.append((fd, path))
            test_options.pop('manual_input')

        net_test_loader = get_net_test_loader(test_options, test_file)
        try:
            net_test_loader.checkOptions()
            d = oonidApplication.director.startNetTest(net_test_loader,
                                                       get_reporters(net_test_loader))
            @d.addBoth
            def cleanup(result):
                for fd, path in tmp_files:
                    os.close(fd)
                    os.remove(path)

        except errors.MissingRequiredOption, option_name:
            self.write({'error':
                        'Missing required option: "%s"' % option_name})
        except usage.UsageError, e:
            self.write({'error':
                        'Error in parsing options'})
        except errors.InsufficientPrivileges:
            self.write({'error':
                        'Insufficient priviledges'})

class StopTest(ORequestHandler):

    @check_xsrf
    def delete(self, test_name):
        pass

def get_test_results(test_id):
    """
    Returns:
        a list of test dicts that correspond to the test results for the given
        test_id.
        The dict is made like so:
        {
            'name': The name of the report,
            'content': The content of the report
        }
    """
    test_results = []
    for test_result in os.listdir(config.reports_directory):
        if test_result.startswith('report-'+test_id):
            with open(os.path.join(config.reports_directory, test_result)) as f:
                test_content = ''.join(f.readlines())
            test_results.append({'name': test_result,
                                 'content': test_content})
    test_results.reverse()
    return test_results

class TestStatus(ORequestHandler):

    @check_xsrf
    def get(self, test_id):
        """
        Returns the requested test_id details and the stored results for such
        test.
        """
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


from __future__ import print_function

import os
import json

from twisted.python import usage
from twisted.python.filepath import FilePath, InsecurePath
from twisted.web import static

from klein import Klein

from ooni.settings import config
from ooni import errors
from ooni.nettest import NetTestLoader
from ooni.measurements import GenerateResults

class RouteNotFound(Exception):
    def __init__(self, path, method):
        self._path = path
        self._method = method

    def __repr__(self):
        return "<RouteNotFound {0} {1}>".format(self._path,
                                                self._method)

def _resolvePath(request):
    path = b''
    if request.postpath:
        path = b'/'.join(request.postpath)

        if not path.startswith(b'/'):
            path = b'/' + path
    return path

def rpath(*path):
    context = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(context, *path)

def getNetTestLoader(test_options, test_file):
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

class WebUIAPI(object):
    app = Klein()

    def __init__(self, config, director):
        self.director = director
        self.config = config

    def render_json(self, obj, request):
        json_string = json.dumps(obj) + "\n"
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Content-Length', len(json_string))
        return json_string

    @app.route('/api/decks/generate', methods=["GET"])
    def generate_decks(self, request):
        return self.render_json({"generate": "deck"}, request)

    @app.route('/api/decks/<string:deck_name>/start', methods=["POST"])
    def start_deck(self, request, deck_name):
        return self.render_json({"start": deck_name}, request)

    @app.route('/api/decks/<string:deck_name>/stop', methods=["POST"])
    def stop_deck(self, request, deck_name):
        return self.render_json({"stop": deck_name}, request)

    @app.route('/api/decks/<string:deck_name>', methods=["GET"])
    def deck_status(self, request, deck_name):
        return self.render_json({"status": deck_name}, request)

    @app.route('/api/decks', methods=["GET"])
    def deck_list(self, request):
        return self.render_json({"command": "deck-list"}, request)

    @app.route('/api/net-tests/<string:test_name>/start', methods=["POST"])
    def test_start(self, request, test_name):
        try:
            net_test = self.director.netTests[test_name]
        except KeyError:
            request.setResponseCode(500)
            return self.render_json({
                'error_code': 500,
                'error_message': 'Could not find the specified test'
            }, request)
        try:
            test_options = json.load(request.content.read())
        except ValueError:
            return self.render_json({
                'error_code': 500,
                'error_message': 'Invalid JSON message recevied'
            }, request)

        net_test_loader = getNetTestLoader(test_options, net_test['path'])
        try:
            net_test_loader.checkOptions()
            # XXX we actually want to generate the report_filename in a smart
            # way so that we can know where it is located and learn the results
            # of the measurement.
            report_filename = None
            self.director.startNetTest(net_test_loader, report_filename)
        except errors.MissingRequiredOption, option_name:
            request.setResponseCode(500)
            return self.render_json({
                'error_code': 501,
                'error_message': ('Missing required option: '
                                  '\'{}\''.format(option_name))
            }, request)
        except usage.UsageError:
            request.setResponseCode(500)
            return self.render_json({
                'error_code': 502,
                'error_message': 'Error in parsing options'
            }, request)
        except errors.InsufficientPrivileges:
            request.setResponseCode(500)
            return self.render_json({
                'error_code': 503,
                'error_message': 'Insufficient priviledges'
            }, request)

        return self.render_json({"deck": "list"}, request)

    @app.route('/api/net-tests/<string:test_name>/start', methods=["POST"])
    def test_stop(self, request, test_name):
        return self.render_json({
            "command": "test-stop",
            "test-name": test_name
        }, request)

    @app.route('/api/net-tests/<string:test_name>', methods=["GET"])
    def test_status(self, request, test_name):
        return self.render_json({"command": "test-stop"}, request)

    @app.route('/api/net-tests', methods=["GET"])
    def test_list(self, request):
        return self.render_json(self.director.netTests, request)

    @app.route('/api/measurement', methods=["GET"])
    def measurement_list(self, request):
        measurement_ids = os.listdir(os.path.join(config.ooni_home,
                                                  "measurements"))
        measurements = []
        for measurement_id in measurement_ids:
            test_start_time, country_code, asn, test_name = \
                measurement_id.split("-")[:4]
            measurements.append({
                "test_name": test_name,
                "country_code": country_code,
                "asn": asn,
                "test_start_time": test_start_time,
                "id": measurement_id
            })
        return self.render_json({"measurements": measurements}, request)

    @app.route('/api/measurement/<string:measurement_id>', methods=["GET"])
    def measurement_summary(self, request, measurement_id):
        measurement_path = FilePath(config.ooni_home).child("measurements")
        try:
            measurement_dir = measurement_path.child(measurement_id)
        except InsecurePath:
            return self.render_json({"error": "invalid measurement id"})

        summary = measurement_dir.child("summary.json")
        measurements = measurement_dir.child("measurements.njson")
        if not summary.exists():
            gr = GenerateResults(measurements.path)
            gr.output(summary.path)

        with summary.open("r") as f:
            r = json.load(f)

        return self.render_json(r, request)

    @app.route('/api/measurement/<string:measurement_id>/<int:idx>',
               methods=["GET"])
    def measurement_open(self, request, measurement_id, idx):
        return self.render_json({"command": "results"}, request)

    @app.route('/client/', branch=True)
    def static(self, request):
        path = rpath("build")
        print(path)
        return static.File(path)


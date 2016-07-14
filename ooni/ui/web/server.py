from __future__ import print_function

import os
import json

from twisted.internet import defer
from twisted.python import usage
from twisted.python.filepath import FilePath, InsecurePath
from twisted.web import static

from klein import Klein
from werkzeug.exceptions import NotFound

from ooni import errors
from ooni.deck import Deck
from ooni.settings import config
from ooni.nettest import NetTestLoader
from ooni.measurements import GenerateResults
from ooni.utils import generate_filename

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
        if v is None:
            print("Skipping %s because none" % k)
            continue
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
        self.active_measurements = {}

    @app.handle_errors(NotFound)
    def not_found(self, request, _):
        request.redirect('/client/')

    def render_json(self, obj, request):
        json_string = json.dumps(obj) + "\n"
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Content-Length', len(json_string))
        return json_string

    @app.route('/api/deck/generate', methods=["GET"])
    def api_deck_generate(self, request):
        return self.render_json({"generate": "deck"}, request)

    @app.route('/api/deck/<string:deck_name>/start', methods=["POST"])
    def api_deck_start(self, request, deck_name):
        return self.render_json({"start": deck_name}, request)

    @app.route('/api/deck', methods=["GET"])
    def api_deck_list(self, request):
        return self.render_json({"command": "deck-list"}, request)

    @defer.inlineCallbacks
    def run_deck(self, deck):
        yield deck.setup()
        measurement_ids = []
        for net_test_loader in deck.netTestLoaders:
            # XXX synchronize this with startNetTest
            test_details = net_test_loader.getTestDetails()
            measurement_id = generate_filename(test_details)

            measurement_dir = os.path.join(
                config.measurements_directory,
                measurement_id
            )
            os.mkdir(measurement_dir)
            report_filename = os.path.join(measurement_dir,
                                           "measurements.njson")
            measurement_ids.append(measurement_id)
            self.active_measurements[measurement_id] = {
                'test_name': test_details['test_name'],
                'test_start_time': test_details['test_start_time']
            }
            self.director.startNetTest(net_test_loader, report_filename)

    @app.route('/api/nettest/<string:test_name>/start', methods=["POST"])
    def api_nettest_start(self, request, test_name):
        try:
            net_test = self.director.netTests[test_name]
        except KeyError:
            request.setResponseCode(500)
            return self.render_json({
                'error_code': 500,
                'error_message': 'Could not find the specified test'
            }, request)
        try:
            test_options = json.load(request.content)
        except ValueError:
            return self.render_json({
                'error_code': 500,
                'error_message': 'Invalid JSON message recevied'
            }, request)

        deck = Deck(no_collector=True) # XXX remove no_collector
        net_test_loader = getNetTestLoader(test_options, net_test['path'])
        try:
            deck.insert(net_test_loader)
            self.run_deck(deck)

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

        return self.render_json({"status": "started"}, request)

    @app.route('/api/nettest', methods=["GET"])
    def api_nettest_list(self, request):
        return self.render_json(self.director.netTests, request)

    @app.route('/api/status', methods=["GET"])
    def api_status(self):
        return self.render_json()

    @app.route('/api/measurement', methods=["GET"])
    def api_measurement_list(self, request):
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
    def api_measurement_summary(self, request, measurement_id):
        measurement_path = FilePath(config.measurements_directory)
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
    def api_measurement_view(self, request, measurement_id, idx):
        measurement_path = FilePath(config.measurements_directory)
        try:
            measurement_dir = measurement_path.child(measurement_id)
        except InsecurePath:
            return self.render_json({"error": "invalid measurement id"})
        measurements = measurement_dir.child("measurements.njson")

        # XXX maybe implement some caching here
        with measurements.open("r") as f:
            r = None
            for f_idx, line in enumerate(f):
                if f_idx == idx:
                    r = json.loads(line)
                    break
            if r is None:
                return self.render_json({"error": "Could not find measurement "
                                                  "with this idx"}, request)
        return self.render_json(r, request)

    @app.route('/client/', branch=True)
    def static(self, request):
        path = rpath("client")
        return static.File(path)
<<<<<<< acda284b56fa3a75acbe7d000fbdefb643839948

=======
>>>>>>> [Web UI] Refactoring of web UI

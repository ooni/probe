from __future__ import print_function

import os
import json

from twisted.internet import defer, task, reactor
from twisted.python import usage
from twisted.python.filepath import FilePath, InsecurePath
from twisted.web import static

from klein import Klein
from werkzeug.exceptions import NotFound

from ooni import __version__ as ooniprobe_version
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


class WebUIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

class WebUIAPI(object):
    app = Klein()
    # Maximum number in seconds after which to return a result even if not
    # change happenned.
    _long_polling_timeout = 5
    _reactor = reactor

    def __init__(self, config, director):
        self.director = director
        self.config = config
        self.measurement_path = FilePath(config.measurements_directory)
        self.decks_path = FilePath(config.decks_directory)

        self.status = {
            "software_version": ooniprobe_version,
            "software_name": "ooniprobe",
            "asn": config.probe_ip.geodata['asn'],
            "country_code": config.probe_ip.geodata['countrycode'],
            "active_measurements": {},
            "completed_measurements": [],
            "director_started": False,
            "failures": []
        }
        self.status_updates = []
        d = self.director.start(start_tor=True)

        d.addCallback(self.director_started)
        d.addErrback(self.director_startup_failed)
        d.addBoth(lambda _: self.broadcast_status_update())

    def add_failure(self, failure):
        self.status['failures'].append(str(failure))

    def director_started(self, _):
        self.status['director_started'] = True
        self.status["asn"] = config.probe_ip.geodata['asn']
        self.status["country_code"] = config.probe_ip.geodata['countrycode']

    def director_startup_failed(self, failure):
        self.add_failure(failure)

    def broadcast_status_update(self):
        for su in self.status_updates:
            if not su.called:
                su.callback(None)

    def completed_measurement(self, measurement_id):
        del self.status['active_measurements'][measurement_id]
        self.status['completed_measurements'].append(measurement_id)
        measurement_dir = self.measurement_path.child(measurement_id)

        measurement = measurement_dir.child('measurements.njson.progress')

        # Generate the summary.json file
        summary = measurement_dir.child('summary.json')
        gr = GenerateResults(measurement.path)
        gr.output(summary.path)

        measurement.moveTo(measurement_dir.child('measurements.njson'))

    def failed_measurement(self, measurement_id, failure):
        del self.status['active_measurements'][measurement_id]
        self.add_failure(str(failure))

    @app.handle_errors(NotFound)
    def not_found(self, request, _):
        request.redirect('/client/')

    @app.handle_error(WebUIError)
    def web_ui_error(self, request, error):
        request.setResponseCode(error.code)
        return self.render_json({
            "error_code": error.code,
            "error_message": error.message
        }, request)

    def render_json(self, obj, request):
        json_string = json.dumps(obj) + "\n"
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Content-Length', len(json_string))
        return json_string

    @app.route('/api/status', methods=["GET"])
    def api_status(self, request):
        return self.render_json(self.status, request)

    @app.route('/api/status/update', methods=["GET"])
    def api_status_update(self, request):
        status_update = defer.Deferred()
        status_update.addCallback(lambda _:
                                  self.status_updates.remove(status_update))
        status_update.addCallback(lambda _: self.api_status(request))

        self.status_updates.append(status_update)

        # After long_polling_timeout we fire the callback
        task.deferLater(self._reactor, self._long_polling_timeout,
                        status_update.callback, None)

        return status_update

    @app.route('/api/deck/generate', methods=["GET"])
    def api_deck_generate(self, request):
        return self.render_json({"generate": "deck"}, request)

    @app.route('/api/deck/<string:deck_name>/start', methods=["POST"])
    def api_deck_start(self, request, deck_name):
        return self.render_json({"start": deck_name}, request)

    @app.route('/api/deck', methods=["GET"])
    def api_deck_list(self, request):
        for deck_id in self.decks_path.listdir():
            pass

        return self.render_json({"command": "deck-list"}, request)

    @defer.inlineCallbacks
    def run_deck(self, deck):
        yield deck.setup()
        measurement_ids = []
        for net_test_loader in deck.netTestLoaders:
            # XXX synchronize this with startNetTest
            test_details = net_test_loader.getTestDetails()
            measurement_id = generate_filename(test_details)

            measurement_dir = self.measurement_path.child(measurement_id)
            measurement_dir.createDirectory()

            report_filename = measurement_dir.child(
                "measurements.njson.progress").path

            measurement_ids.append(measurement_id)
            self.status['active_measurements'][measurement_id] = {
                'test_name': test_details['test_name'],
                'test_start_time': test_details['test_start_time']
            }
            self.broadcast_status_update()
            d = self.director.startNetTest(net_test_loader, report_filename)
            d.addCallback(lambda _:
                          self.completed_measurement(measurement_id))
            d.addErrback(lambda failure:
                         self.failed_measurement(measurement_id, failure))

    @app.route('/api/nettest/<string:test_name>/start', methods=["POST"])
    def api_nettest_start(self, request, test_name):
        try:
            net_test = self.director.netTests[test_name]
        except KeyError:
            raise WebUIError(500, 'Could not find the specified test')

        try:
            test_options = json.load(request.content)
        except ValueError:
            raise WebUIError(500, 'Invalid JSON message recevied')

        deck = Deck(no_collector=True) # XXX remove no_collector
        net_test_loader = getNetTestLoader(test_options, net_test['path'])
        try:
            deck.insert(net_test_loader)
            self.run_deck(deck)

        except errors.MissingRequiredOption, option_name:
            raise WebUIError(
                501, 'Missing required option: "{}"'.format(option_name)
            )

        except usage.UsageError:
            raise WebUIError(
                502, 'Error in parsing options'
            )

        except errors.InsufficientPrivileges:
            raise WebUIError(
                502, 'Insufficient priviledges'
            )

        return self.render_json({"status": "started"}, request)

    @app.route('/api/nettest', methods=["GET"])
    def api_nettest_list(self, request):
        return self.render_json(self.director.netTests, request)

    @app.route('/api/input', methods=["GET"])
    def api_input_list(self, request):
        return self.render_json(self.director.input_store.list(), request)

    @app.route('/api/measurement', methods=["GET"])
    def api_measurement_list(self, request):
        measurements = []
        for measurement_id in self.measurement_path.listdir():
            measurement = self.measurement_path.child(measurement_id)
            completed = True
            if measurement.child("measurement.njson.progress").exists():
                completed = False
            test_start_time, country_code, asn, test_name = \
                measurement_id.split("-")[:4]
            measurements.append({
                "test_name": test_name,
                "country_code": country_code,
                "asn": asn,
                "test_start_time": test_start_time,
                "id": measurement_id,
                "completed": completed
            })
        return self.render_json({"measurements": measurements}, request)

    @app.route('/api/measurement/<string:measurement_id>', methods=["GET"])
    def api_measurement_summary(self, request, measurement_id):
        try:
            measurement_dir = self.measurement_path.child(measurement_id)
        except InsecurePath:
            raise WebUIError(500, "invalid measurement id")

        if measurement_dir.child("measurements.njson.progress").exists():
            raise WebUIError(400, "measurement in progress")

        summary = measurement_dir.child("summary.json")
        with summary.open("r") as f:
            r = json.load(f)

        return self.render_json(r, request)

    @app.route('/api/measurement/<string:measurement_id>/<int:idx>',
               methods=["GET"])
    def api_measurement_view(self, request, measurement_id, idx):
        try:
            measurement_dir = self.measurement_path.child(measurement_id)
        except InsecurePath:
            raise WebUIError(500, "Invalid measurement id")

        measurements = measurement_dir.child("measurements.njson")

        # This gets the line idx of the measurement file.
        # XXX maybe implement some caching here
        with measurements.open("r") as f:
            r = None
            for f_idx, line in enumerate(f):
                if f_idx == idx:
                    r = json.loads(line)
                    break
            if r is None:
                raise WebUIError(404, "Could not find measurement with this idx")
        return self.render_json(r, request)

    @app.route('/client/', branch=True)
    def static(self, request):
        path = rpath("client")
        return static.File(path)
<<<<<<< acda284b56fa3a75acbe7d000fbdefb643839948

=======
>>>>>>> [Web UI] Refactoring of web UI

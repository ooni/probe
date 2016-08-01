from __future__ import print_function

import json
import string
from functools import wraps
from random import SystemRandom

from twisted.internet import defer, task, reactor
from twisted.python import usage
from twisted.python.filepath import FilePath, InsecurePath
from twisted.web import static

from klein import Klein
from werkzeug.exceptions import NotFound

from ooni import __version__ as ooniprobe_version
from ooni import errors
from ooni.deck import NGDeck
from ooni.deck.store import DeckNotFound, InputNotFound
from ooni.settings import config
from ooni.utils import log
from ooni.director import DirectorEvent
from ooni.measurements import get_summary, get_measurement, list_measurements
from ooni.measurements import MeasurementNotFound, MeasurementInProgress
from ooni.geoip import probe_ip

config.advanced.debug = True

class WebUIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


def xsrf_protect(check=True):
    """
    This is a decorator that implements double submit token CSRF protection.

    Basically we set a cookie and ensure that every request contains the
    same value inside of the cookie and the request header.

    It's based on the assumption that an attacker cannot read the cookie
    that is set by the server (since it would be violating the SOP) and hence
    is not possible to make a browser trigger requests that contain the
    cookie value inside of the requests it sends.

    If you wish to disable checking of the token set the value check to False.
    This will still lead to the cookie being set.

    This decorator needs to be applied after the decorator that registers
    the routes.
    """
    def deco(f):

        @wraps(f)
        def wrapper(instance, request, *a, **kw):
            should_check = check and instance._enable_xsrf_protection
            token_cookie = request.getCookie(u'XSRF-TOKEN')
            token_header = request.getHeader(b"X-XSRF-TOKEN")
            if (token_cookie != instance._xsrf_token and
                    instance._enable_xsrf_protection):
                request.addCookie(u'XSRF-TOKEN',
                                  instance._xsrf_token,
                                  path=u'/')
            if should_check and token_cookie != token_header:
                raise WebUIError(404, "Invalid XSRF token")
            return f(instance, request, *a, **kw)

        return wrapper

    return deco



class LongPoller(object):
    def __init__(self, timeout, _reactor=reactor):
        self.lock = defer.DeferredLock()

        self.deferred_subscribers = []
        self._reactor = _reactor
        self._timeout = timeout

        self.timer = task.LoopingCall(
            self.notify,
            DirectorEvent("null", "No updates"),
        )
        self.timer.clock = self._reactor

    def start(self):
        self.timer.start(self._timeout)

    def stop(self):
        self.timer.stop()

    def _notify(self, lock, event):
        for d in self.deferred_subscribers[:]:
            assert not d.called, "Deferred is already called"
            d.callback(event)
            self.deferred_subscribers.remove(d)
        self.timer.reset()
        lock.release()

    def notify(self, event=None):
        self.lock.acquire().addCallback(self._notify, event)

    def get(self):
        d = defer.Deferred()
        self.deferred_subscribers.append(d)
        return d

class WebUIAPI(object):
    app = Klein()
    # Maximum number in seconds after which to return a result even if not
    # change happenned.
    _long_polling_timeout = 5
    _reactor = reactor
    _enable_xsrf_protection = True

    def __init__(self, config, director, _reactor=reactor):
        self.director = director
        self.config = config
        self.measurement_path = FilePath(config.measurements_directory)

        # We use a double submit token to protect against XSRF
        rng = SystemRandom()
        token_space = string.letters+string.digits
        self._xsrf_token = ''.join([rng.choice(token_space)
                                    for _ in range(30)])

        self._director_started = False

        self.status_poller = LongPoller(
            self._long_polling_timeout, _reactor)
        self.director_event_poller = LongPoller(
            self._long_polling_timeout, _reactor)

        # XXX move this elsewhere
        self.director_event_poller.start()
        self.status_poller.start()

        self.director.subscribe(self.handle_director_event)
        d = self.director.start()

        d.addCallback(self.director_started)
        d.addBoth(lambda _: self.status_poller.notify())

    @property
    def status(self):
        return {
            "software_version": ooniprobe_version,
            "software_name": "ooniprobe",
            "asn": probe_ip.geodata['asn'],
            "country_code": probe_ip.geodata['countrycode'],
            "director_started": self._director_started
        }

    def handle_director_event(self, event):
        log.msg("Handling event {0}".format(event.type))
        self.director_event_poller.notify(event)

    def director_started(self, _):
        self._director_started = True

    @app.handle_errors(NotFound)
    @xsrf_protect(check=False)
    def not_found(self, request, _):
        request.redirect('/client/')

    @app.handle_errors(WebUIError)
    @xsrf_protect(check=False)
    def web_ui_error(self, request, failure):
        error = failure.value
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

    @app.route('/api/notify', methods=["GET"])
    @xsrf_protect(check=False)
    def api_notify(self, request):
        def got_director_event(event):
            return self.render_json({
                "type": event.type,
                "message": event.message
            }, request)
        d = self.director_event_poller.get()
        d.addCallback(got_director_event)
        return d

    @app.route('/api/status', methods=["GET"])
    @xsrf_protect(check=False)
    def api_status(self, request):
        return self.render_json(self.status, request)

    @app.route('/api/status/update', methods=["GET"])
    @xsrf_protect(check=False)
    def api_status_update(self, request):
        def got_status_update(event):
            return self.api_status(request)
        d = self.status_poller.get()
        d.addCallback(got_status_update)
        return d

    @app.route('/api/deck/<string:deck_id>/start', methods=["POST"])
    @xsrf_protect(check=True)
    def api_deck_start(self, request, deck_id):
        try:
            deck = self.director.deck_store.get(deck_id)
        except DeckNotFound:
            raise WebUIError(404, "Deck not found")

        try:
            self.run_deck(deck)
        except:
            raise WebUIError(500, "Failed to start deck")

        return self.render_json({"status": "started " + deck.name}, request)

    @app.route('/api/deck', methods=["GET"])
    @xsrf_protect(check=False)
    def api_deck_list(self, request):
        deck_list = {
            'available': {},
            'enabled': {}
        }
        for deck_id, deck in self.director.deck_store.list():
            deck_list['available'][deck_id] = {
                'name': deck.name,
                'description': deck.description
            }

        for deck_id, deck in self.director.deck_store.list_enabled():
            deck_list['enabled'][deck_id] = {
                'name': deck.name,
                'description': deck.description
            }

        return self.render_json(deck_list, request)

    @app.route('/api/deck/<string:deck_id>/enable', methods=["POST"])
    @xsrf_protect(check=True)
    def api_deck_enable(self, request, deck_id):
        try:
            self.director.deck_store.enable(deck_id)
        except DeckNotFound:
            raise WebUIError(404, "Deck not found")

        return self.render_json({"status": "enabled"}, request)

    @app.route('/api/deck/<string:deck_id>/disable', methods=["POST"])
    @xsrf_protect(check=True)
    def api_deck_disable(self, request, deck_id):
        try:
            self.director.deck_store.disable(deck_id)
        except DeckNotFound:
            raise WebUIError(404, "Deck not found")

        return self.render_json({"status": "disabled"}, request)

    @defer.inlineCallbacks
    def run_deck(self, deck):
        # These are dangling deferreds
        try:
            yield deck.setup()
            yield deck.run(self.director)
        except:
            self.director_event_poller.notify(DirectorEvent("error",
                                                            "Failed to start deck"))

    @app.route('/api/nettest/<string:test_name>/start', methods=["POST"])
    @xsrf_protect(check=True)
    def api_nettest_start(self, request, test_name):
        try:
            _ = self.director.netTests[test_name]
        except KeyError:
            raise WebUIError(500, 'Could not find the specified test')

        try:
            test_options = json.load(request.content)
        except ValueError:
            raise WebUIError(500, 'Invalid JSON message recevied')

        test_options["test_name"] = test_name
        deck_data = {
            "tasks": [
                {"ooni": test_options}
            ]
        }
        try:
            deck = NGDeck(no_collector=True)
            deck.load(deck_data)
            self.run_deck(deck)

        except errors.MissingRequiredOption, option_name:
            raise WebUIError(
                400, 'Missing required option: "{}"'.format(option_name)
            )

        except usage.UsageError:
            raise WebUIError(
                400, 'Error in parsing options'
            )

        except errors.InsufficientPrivileges:
            raise WebUIError(
                400, 'Insufficient priviledges'
            )
        except:
            raise WebUIError(
                500, 'Failed to start nettest'
            )

        return self.render_json({"status": "started"}, request)

    @app.route('/api/nettest', methods=["GET"])
    @xsrf_protect(check=False)
    def api_nettest_list(self, request):
        return self.render_json(self.director.netTests, request)

    @app.route('/api/input', methods=["GET"])
    @xsrf_protect(check=False)
    def api_input_list(self, request):
        input_store_list = self.director.input_store.list()
        for key, value in input_store_list.items():
            value.pop('filepath')
        return self.render_json(input_store_list, request)

    @app.route('/api/input/<string:input_id>/content', methods=["GET"])
    @xsrf_protect(check=False)
    def api_input_content(self, request, input_id):
        content = self.director.input_store.getContent(input_id)
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Content-Length', len(content))
        return content

    @app.route('/api/input/<string:input_id>', methods=["GET"])
    @xsrf_protect(check=False)
    def api_input_details(self, request, input_id):
        return self.render_json(
            self.director.input_store.get(input_id), request
        )

    @app.route('/api/measurement', methods=["GET"])
    @xsrf_protect(check=False)
    def api_measurement_list(self, request):
        measurements = list_measurements()
        return self.render_json({"measurements": measurements}, request)

    @app.route('/api/measurement/<string:measurement_id>', methods=["GET"])
    @xsrf_protect(check=False)
    def api_measurement_summary(self, request, measurement_id):
        try:
            measurement = get_measurement(measurement_id)
        except InsecurePath:
            raise WebUIError(500, "invalid measurement id")
        except MeasurementNotFound:
            raise WebUIError(404, "measurement not found")
        except MeasurementInProgress:
            raise WebUIError(400, "measurement in progress")

        if measurement['completed'] is False:
            raise WebUIError(400, "measurement in progress")

        summary = get_summary(measurement_id)
        return self.render_json(summary, request)

    @app.route('/api/measurement/<string:measurement_id>', methods=["DELETE"])
    @xsrf_protect(check=True)
    def api_measurement_delete(self, request, measurement_id):
        try:
            measurement = get_measurement(measurement_id)
        except InsecurePath:
            raise WebUIError(500, "invalid measurement id")
        except MeasurementNotFound:
            raise WebUIError(404, "measurement not found")

        if measurement['running'] is True:
            raise WebUIError(400, "Measurement running")

        try:
            measurement_dir = self.measurement_path.child(measurement_id)
            measurement_dir.remove()
        except:
            raise WebUIError(400, "Failed to delete report")

        return self.render_json({"result": "ok"}, request)

    @app.route('/api/measurement/<string:measurement_id>/keep', methods=["POST"])
    @xsrf_protect(check=True)
    def api_measurement_keep(self, request, measurement_id):
        try:
            measurement_dir = self.measurement_path.child(measurement_id)
        except InsecurePath:
            raise WebUIError(500, "invalid measurement id")

        summary = measurement_dir.child("keep")
        with summary.open("w+") as f:
            pass

        return self.render_json({"status": "ok"}, request)

    @app.route('/api/measurement/<string:measurement_id>/<int:idx>',
               methods=["GET"])
    @xsrf_protect(check=False)
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
    @xsrf_protect(check=False)
    def static(self, request):
        return static.File(config.web_ui_directory)

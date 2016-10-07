from __future__ import print_function

import os
import json
import errno
import string
import random
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
            token_cookie = request.getCookie(b'XSRF-TOKEN')
            token_header = request.getHeader(b"X-XSRF-TOKEN")
            if (token_cookie != instance._xsrf_token and
                    instance._enable_xsrf_protection):
                request.addCookie(b'XSRF-TOKEN',
                                  instance._xsrf_token,
                                  path=b'/')
            if should_check and token_cookie != token_header:
                raise WebUIError(404, "Invalid XSRF token")
            return f(instance, request, *a, **kw)

        return wrapper

    return deco


def _requires_value(value, attrs=[]):

    def deco(f):

        @wraps(f)
        def wrapper(instance, request, *a, **kw):
            for attr in attrs:
                attr_value = getattr(instance, attr)
                if attr_value is not value:
                    raise WebUIError(400, "{0} must be {1}".format(attr,
                                                                   value))
            return f(instance, request, *a, **kw)

        return wrapper

    return deco

def requires_true(attrs=[]):
    """
    This decorator is used to require that a certain set of class attributes are
    set to True.
    Otherwise it will trigger a WebUIError.
    """
    return _requires_value(True, attrs)

def requires_false(attrs=[]):
    """
    This decorator is used to require that a certain set of class attributes are
    set to False.
    Otherwise it will trigger a WebUIError.
    """
    return _requires_value(False, attrs)


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
    # Maximum number in seconds after which to return a result even if no
    # change happened.
    _long_polling_timeout = 5
    _reactor = reactor
    _enable_xsrf_protection = True

    def __init__(self, config, director, scheduler, _reactor=reactor):
        self._reactor = reactor
        self.director = director
        self.scheduler = scheduler

        self.config = config
        self.measurement_path = FilePath(config.measurements_directory)

        # We use a double submit token to protect against XSRF
        rng = SystemRandom()
        token_space = string.letters+string.digits
        self._xsrf_token = b''.join([rng.choice(token_space)
                                    for _ in range(30)])

        self._director_started = False
        self._is_initialized = config.is_initialized()

        # We use exponential backoff to trigger retries of the startup of
        # the director.
        self._director_startup_retries = 0
        # Maximum delay should be 6 hours
        self._director_max_retry_delay = 6*60*60

        self.status_poller = LongPoller(
            self._long_polling_timeout, _reactor)
        self.director_event_poller = LongPoller(
            self._long_polling_timeout, _reactor)

        # XXX move this elsewhere
        self.director_event_poller.start()
        self.status_poller.start()

        self.director.subscribe(self.handle_director_event)
        if self._is_initialized:
            self.start_director()

    def start_director(self):
        log.debug("Starting director")
        d = self.director.start()

        d.addCallback(self.director_started)
        d.addErrback(self.director_startup_failed)
        d.addBoth(lambda _: self.status_poller.notify())

    @property
    def status(self):
        quota_warning = None
        try:
            with open(os.path.join(config.running_path,
                                   "quota_warning")) as in_file:
                quota_warning = in_file.read()
        except IOError as ioe:
            if ioe.errno != errno.ENOENT:
                raise
        return {
            "software_version": ooniprobe_version,
            "software_name": "ooniprobe",
            "asn": probe_ip.geodata['asn'],
            "country_code": probe_ip.geodata['countrycode'],
            "director_started": self._director_started,
            "initialized": self._is_initialized,
            "quota_warning": quota_warning
        }

    def handle_director_event(self, event):
        log.debug("Handling event {0}".format(event.type))
        self.director_event_poller.notify(event)

    def director_startup_failed(self, failure):
        self._director_startup_retries += 1

        # We delay the startup using binary exponential backoff with an
        # upper bound.
        startup_delay = random.uniform(
            0, min(2**self._director_startup_retries,
                   self._director_max_retry_delay)
        )
        log.err("Failed to start the director, "
                "retrying in {0}s".format(startup_delay))
        self._reactor.callLater(
            startup_delay,
            self.start_director
        )

    def director_started(self, _):
        log.debug("Started director")
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

    @app.route('/api/initialize', methods=["GET"])
    @xsrf_protect(check=False)
    @requires_false(attrs=['_is_initialized'])
    def api_initialize_get(self, request):
        available_decks = []
        for deck_id, deck in self.director.deck_store.list():
            available_decks.append({
                'name': deck.name,
                'description': deck.description,
                'schedule': deck.schedule,
                'enabled': self.director.deck_store.is_enabled(deck_id),
                'id': deck_id
            })
        return self.render_json({"available_decks": available_decks}, request)

    @app.route('/api/initialize', methods=["POST"])
    @xsrf_protect(check=True)
    @requires_false(attrs=['_is_initialized'])
    def api_initialize(self, request):
        try:
            initial_configuration = json.load(request.content)
        except ValueError:
            raise WebUIError(400, 'Invalid JSON message recevied')

        required_keys = ['include_ip', 'include_asn', 'include_country',
                         'should_upload', 'preferred_backend']
        options = {}
        for required_key in required_keys:
            try:
                options[required_key] = initial_configuration[required_key]
            except KeyError:
                raise WebUIError(400, 'Missing required key {0}'.format(
                    required_key))
        config.create_config_file(**options)
        try:
            deck_config = initial_configuration['deck_config']
        except KeyError:
            raise WebUIError(400, 'Missing enabled decks')

        for deck_id, enabled in deck_config.items():
            try:
                if enabled is True:
                    self.director.deck_store.enable(deck_id)
                elif enabled is False:
                    try:
                        self.director.deck_store.disable(deck_id)
                    except DeckNotFound:
                        # We ignore these errors, because it could be that a deck
                        # that is marked as disabled is already disabled
                        pass
            except DeckNotFound:
                raise WebUIError(404, 'Deck not found')

        self.scheduler.refresh_deck_list()
        config.set_initialized()

        self._is_initialized = True

        self.status_poller.notify()
        self.start_director()
        return self.render_json({"result": "ok"}, request)

    @app.route('/api/deck/<string:deck_id>/start', methods=["POST"])
    @xsrf_protect(check=True)
    @requires_true(attrs=['_director_started', '_is_initialized'])
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
    @requires_true(attrs=['_director_started', '_is_initialized'])
    def api_deck_list(self, request):
        deck_list = {
            'available': {},
            'enabled': {}
        }
        for deck_id, deck in self.director.deck_store.list():
            deck_list['available'][deck_id] = {
                'name': deck.name,
                'description': deck.description,
                'schedule': deck.schedule,
                'enabled': self.director.deck_store.is_enabled(deck_id)
            }

        for deck_id, deck in self.director.deck_store.list_enabled():
            deck_list['enabled'][deck_id] = {
                'name': deck.name,
                'description': deck.description,
                'schedule': deck.schedule,
                'enabled': True
            }

        return self.render_json(deck_list, request)

    @app.route('/api/deck/<string:deck_id>/run', methods=["POST"])
    @xsrf_protect(check=True)
    @requires_true(attrs=['_director_started', '_is_initialized'])
    def api_deck_run(self, request, deck_id):
        try:
            deck = self.director.deck_store.get(deck_id)
        except DeckNotFound:
            raise WebUIError(404, "Deck not found")

        self.run_deck(deck)

        return self.render_json({"status": "starting"}, request)

    @app.route('/api/deck/<string:deck_id>/enable', methods=["POST"])
    @xsrf_protect(check=True)
    @requires_true(attrs=['_director_started', '_is_initialized'])
    def api_deck_enable(self, request, deck_id):
        try:
            self.director.deck_store.enable(deck_id)
        except DeckNotFound:
            raise WebUIError(404, "Deck not found")

        self.scheduler.refresh_deck_list()

        return self.render_json({"status": "enabled"}, request)

    @app.route('/api/deck/<string:deck_id>/disable', methods=["POST"])
    @xsrf_protect(check=True)
    @requires_true(attrs=['_director_started', '_is_initialized'])
    def api_deck_disable(self, request, deck_id):
        try:
            self.director.deck_store.disable(deck_id)
        except DeckNotFound:
            raise WebUIError(404, "Deck not found")
        self.scheduler.refresh_deck_list()

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
    @requires_true(attrs=['_director_started', '_is_initialized'])
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
            deck = NGDeck()
            deck.load(deck_data)
            self.run_deck(deck)

        except errors.MissingRequiredOption as option_name:
            raise WebUIError(
                400, 'Missing required option: "{}"'.format(option_name)
            )

        except usage.UsageError:
            raise WebUIError(
                400, 'Error in parsing options'
            )

        except errors.InsufficientPrivileges:
            raise WebUIError(
                400, 'Insufficient privileges'
            )
        except:
            raise WebUIError(
                500, 'Failed to start nettest'
            )

        return self.render_json({"status": "started"}, request)

    @app.route('/api/nettest', methods=["GET"])
    @xsrf_protect(check=False)
    @requires_true(attrs=['_director_started', '_is_initialized'])
    def api_nettest_list(self, request):
        return self.render_json(self.director.netTests, request)

    @app.route('/api/input', methods=["GET"])
    @xsrf_protect(check=False)
    @requires_true(attrs=['_is_initialized'])
    def api_input_list(self, request):
        input_store_list = self.director.input_store.list()
        for key, value in input_store_list.items():
            value.pop('filepath')
        return self.render_json(input_store_list, request)

    @app.route('/api/input/<string:input_id>/content', methods=["GET"])
    @xsrf_protect(check=False)
    @requires_true(attrs=['_is_initialized'])
    def api_input_content(self, request, input_id):
        content = self.director.input_store.getContent(input_id)
        request.setHeader('Content-Type', 'text/plain')
        request.setHeader('Content-Length', len(content))
        return content

    @app.route('/api/input/<string:input_id>', methods=["GET"])
    @xsrf_protect(check=False)
    @requires_true(attrs=['_is_initialized'])
    def api_input_details(self, request, input_id):
        input_desc = self.director.input_store.get(input_id)
        input_desc.pop('filepath')
        return self.render_json(
            input_desc, request
        )

    @app.route('/api/measurement', methods=["GET"])
    @xsrf_protect(check=False)
    @requires_true(attrs=['_is_initialized'])
    def api_measurement_list(self, request):
        measurements = list_measurements()
        return self.render_json({"measurements": measurements}, request)

    @app.route('/api/measurement/<string:measurement_id>', methods=["GET"])
    @xsrf_protect(check=False)
    @requires_true(attrs=['_is_initialized'])
    @defer.inlineCallbacks
    def api_measurement_summary(self, request, measurement_id):
        log.warn("SUMMARY")
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

        summary = yield get_summary(measurement_id)
        defer.returnValue(self.render_json(summary, request))

    @app.route('/api/measurement/<string:measurement_id>', methods=["DELETE"])
    @xsrf_protect(check=True)
    @requires_true(attrs=['_is_initialized'])
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
    @requires_true(attrs=['_is_initialized'])
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
    @requires_true(attrs=['_is_initialized'])
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

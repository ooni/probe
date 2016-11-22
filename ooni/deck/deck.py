import os
import uuid
import errno
from copy import deepcopy
from string import Template

import yaml
from twisted.internet import defer
from twisted.python.filepath import FilePath

from ooni import errors as e
from ooni.backend_client import BouncerClient, CollectorClient
from ooni.backend_client import get_preferred_bouncer
from ooni.deck.backend import lookup_collector_and_test_helpers
from ooni.deck.legacy import convert_legacy_deck
from ooni.geoip import probe_ip
from ooni.nettest import NetTestLoader, nettest_to_path
from ooni.measurements import generate_summary
from ooni.settings import config
from ooni.utils import log, generate_filename


def resolve_file_path(v, prepath=None):
    from ooni.deck.store import input_store
    if v.startswith("$"):
        # This raises InputNotFound and we let it carry onto the caller
        return input_store.get(v[1:])["filepath"]
    if prepath is not None and (not os.path.isabs(v)):
        return FilePath(prepath).preauthChild(v).path
    return v


def options_to_args(options):
    args = []
    for k, v in options.items():
        if v is None:
            continue
        if v == False or v == 0:
            continue
        if (len(k)) == 1:
            args.append('-'+k)
        else:
            args.append('--'+k)
        if isinstance(v, bool) or isinstance(v, int):
            continue
        args.append(v)
    return args


def normalize_options(options):
    """
    Takes some options that have a mixture of - and _ and returns the
    equivalent options with only '_'.
    """
    normalized_opts = {}
    for k, v in options.items():
        normalized_key = k.replace('-', '_')
        assert normalized_key not in normalized_opts, "The key {0} cannot be normalized".format(k)
        normalized_opts[normalized_key] = v
    return normalized_opts


class UnknownTaskKey(Exception):
    pass


class MissingTaskDataKey(Exception):
    pass


class NGDeck(object):
    def __init__(self,
                 deck_data=None,
                 deck_path=None,
                 global_options={},
                 no_collector=False,
                 arbitrary_paths=False):
        # Used to resolve relative paths inside of decks.
        self.deck_directory = os.getcwd()
        self.requires_tor = False
        self.no_collector = no_collector
        self.name = ""
        self.description = ""
        self.schedule = None

        self.metadata = {}
        self.global_options = normalize_options(global_options)
        self.bouncer = None

        self._arbitrary_paths = arbitrary_paths
        self._is_setup = False

        self._measurement_path = FilePath(config.measurements_directory)
        self._tasks = []

        if deck_path is not None:
            self.open(deck_path)
        elif deck_data is not None:
            self.load(deck_data)

    def open(self, deck_path, global_options=None):
        with open(deck_path) as fh:
            deck_data = yaml.safe_load(fh)
        self.deck_directory = os.path.abspath(os.path.dirname(deck_path))
        self.load(deck_data, global_options)

    def load(self, deck_data, global_options=None):
        if global_options is not None:
            self.global_options = normalize_options(global_options)

        if isinstance(deck_data, list):
            deck_data = convert_legacy_deck(deck_data)

        self.name = deck_data.pop("name", "Un-named Deck")
        self.description = deck_data.pop("description", "No description")

        bouncer_address = self.global_options.get('bouncer',
                                                  deck_data.pop("bouncer", None))
        if bouncer_address is None:
            self.bouncer = get_preferred_bouncer()
        elif isinstance(bouncer_address, dict):
            self.bouncer = BouncerClient(settings=bouncer_address)
        else:
            self.bouncer = BouncerClient(bouncer_address)

        self.schedule = deck_data.pop("schedule", None)

        tasks_data = deck_data.pop("tasks", [])
        for key, metadata in deck_data.items():
            self.metadata[key] = metadata

        # We override the task metadata with the global options if present
        self.metadata.update(self.global_options)

        for task_data in tasks_data:
            deck_task = DeckTask(
                data=task_data,
                parent_metadata=self.metadata,
                global_options=self.global_options,
                cwd=self.deck_directory,
                arbitrary_paths=self._arbitrary_paths
            )
            if deck_task.requires_tor:
                self.requires_tor = True
            if (deck_task.requires_bouncer and
                    self.bouncer.backend_type == "onion"):
                self.requires_tor = True
            self._tasks.append(deck_task)

        if self.metadata.get('no_collector', False):
            self.no_collector = True

    @property
    def tasks(self):
        return self._tasks

    def write(self, fh):
        """
        Writes a properly formatted deck to the supplied file handle.
        :param fh: an open file handle
        :return:
        """
        deck_data = {
            "name": self.name,
            "description": self.description,
            "tasks": [task.data for task in self._tasks]
        }
        if self.schedule is not None:
            deck_data["schedule"] = self.schedule
        for key, value in self.metadata.items():
            deck_data[key] = value

        fh.write("---\n")
        yaml.safe_dump(deck_data, fh, default_flow_style=False)

    @defer.inlineCallbacks
    def query_bouncer(self):
        preferred_backend = config.advanced.get(
            "preferred_backend", "onion"
        )
        log.msg("Looking up collector and test helpers with {0}".format(
            self.bouncer.base_address)
        )
        net_test_loaders = []
        for task in self._tasks:
            if task.type == "ooni":
                net_test_loaders.append(task.ooni["net_test_loader"])

        yield lookup_collector_and_test_helpers(
            net_test_loaders,
            self.bouncer,
            preferred_backend,
            self.no_collector
        )
        defer.returnValue(net_test_loaders)

    def _measurement_completed(self, result, task):
        if not task.output_path:
            measurement_id = task.id
            measurement_dir = self._measurement_path.child(measurement_id)
            measurement_dir.child("measurements.njson.progress").moveTo(
                measurement_dir.child("measurements.njson")
            )
            generate_summary(
                measurement_dir.child("measurements.njson").path,
                measurement_dir.child("summary.json").path
            )
            measurement_dir.child("running.pid").remove()

    def _measurement_failed(self, failure, task):
        if not task.output_path:
            # XXX do we also want to delete measurements.njson.progress?
            measurement_id = task.id
            measurement_dir = self._measurement_path.child(measurement_id)
            measurement_dir.child("running.pid").remove()
        return failure

    def _run_ooni_task(self, task, director):
        net_test_loader = task.ooni["net_test_loader"]
        # XXX-REFACTOR we do this so late to avoid the collision between the
        #  same id and hence generating the same filename.
        test_details = net_test_loader.getTestDetails()
        task.id = generate_filename(test_details)

        measurement_id = None
        report_filename = task.output_path
        if not task.output_path:
            measurement_id = task.id

            measurement_dir = self._measurement_path.child(measurement_id)
            try:
                measurement_dir.createDirectory()
            except OSError as ose:
                if ose.errno == errno.EEXIST:
                    raise Exception("Directory already exists, there is a "
                                    "collision")

            report_filename = measurement_dir.child("measurements.njson.progress").path
            pid_file = measurement_dir.child("running.pid")

            with pid_file.open('w') as out_file:
                out_file.write("{0}".format(os.getpid()))

        d = director.start_net_test_loader(
            net_test_loader,
            report_filename,
            collector_client=net_test_loader.collector,
            test_details=test_details,
            measurement_id=measurement_id
        )
        d.addCallback(self._measurement_completed, task)
        d.addErrback(self._measurement_failed, task)
        return d

    @defer.inlineCallbacks
    def setup(self):
        """
        This method needs to be called before you are able to run a deck.
        """
        from ooni.deck.store import InputNotFound
        for task in self._tasks:
            try:
                yield task.setup()
            except InputNotFound:
                log.msg("Skipping the task {0} because the input cannot be "
                        "found".format(task.id))
                task.skip = True
        self._is_setup = True

    @defer.inlineCallbacks
    def run(self, director):
        assert self._is_setup, "You must call setup() before you can run a " \
                               "deck"
        if self.requires_tor:
            yield director.start_tor()
        yield self.query_bouncer()
        for task in self._tasks:
            if task.skip is True:
                log.msg("Skipping running {0}".format(task.id))
                continue
            if task.type == "ooni":
                yield self._run_ooni_task(task, director)
        self._is_setup = False


class DeckTask(object):
    _metadata_keys = ["name"]
    _supported_tasks = ["ooni"]

    def __init__(self, data,
                 parent_metadata={},
                 global_options={},
                 cwd=None,
                 arbitrary_paths=False):

        self.parent_metadata = normalize_options(parent_metadata)
        self.global_options = global_options
        self.cwd = cwd
        self.data = deepcopy(data)

        self.skip = False

        self.id = "invalid"

        self.type = None
        self.metadata = {}
        self.requires_tor = False
        self.requires_bouncer = False

        # If this is set to true a deck can specify any path. It should only
        #  be run against trusted decks or when you create a deck
        # programmaticaly to a run test specified from the command line.
        self._arbitrary_paths = arbitrary_paths

        self.ooni = {
            'bouncer_client': None,
            'test_details': {}
        }
        self.output_path = None

        self._load(data)

    def _pop_option(self, name, task_data, default=None):
        try:
            value = self.global_options[name]
            if value in [None, 0]:
                raise KeyError
        except KeyError:
            value = task_data.pop(name,
                                  self.parent_metadata.get(name, default))
        task_data.pop(name, None)
        return value

    def _load_ooni(self, task_data):
        required_keys = ["test_name"]
        for required_key in required_keys:
            if required_key not in task_data:
                raise MissingTaskDataKey(required_key)

        # This raises e.NetTestNotFound, we let it go onto the caller
        nettest_path = nettest_to_path(task_data.pop("test_name"),
                                       self._arbitrary_paths)

        annotations = self._pop_option('annotations', task_data, {})
        collector_address = self._pop_option('collector', task_data, None)

        try:
            self.output_path = self.global_options['reportfile']
        except KeyError:
            self.output_path = task_data.pop('reportfile', None)

        if task_data.get('no-collector', False):
            collector_address = None
        elif config.reports.upload is False:
            collector_address = None

        net_test_loader = NetTestLoader(
            options_to_args(task_data),
            annotations=annotations,
            test_file=nettest_path
        )

        if isinstance(collector_address, dict):
            net_test_loader.collector = CollectorClient(
                settings=collector_address
            )
        elif collector_address is not None:
            net_test_loader.collector = CollectorClient(
                collector_address
            )

        if (net_test_loader.collector is not None and
                net_test_loader.collector.backend_type == "onion"):
            self.requires_tor = True

        try:
            net_test_loader.checkOptions()
            if net_test_loader.requiresTor:
                self.requires_tor = True
        except e.MissingTestHelper:
            self.requires_bouncer = True

        self.ooni['net_test_loader'] = net_test_loader

    @defer.inlineCallbacks
    def _setup_ooni(self):
        yield probe_ip.lookup()
        for input_file in self.ooni['net_test_loader'].inputFiles:
            filename = Template(input_file['filename']).safe_substitute(
                probe_cc=probe_ip.geodata['countrycode'].lower()
            )
            file_path = resolve_file_path(filename, self.cwd)
            input_file['test_options'][input_file['key']] = file_path

    def setup(self):
        self.id = str(uuid.uuid4())
        return getattr(self, "_setup_"+self.type)()

    def _load(self, data):
        for key in self._metadata_keys:
            try:
                self.metadata[key] = data.pop(key)
            except KeyError:
                continue

        task_type, task_data = data.popitem()
        if task_type not in self._supported_tasks:
            raise UnknownTaskKey(task_type)
        self.type = task_type
        getattr(self, "_load_"+task_type)(task_data)
        assert len(data) == 0, "Got an unidentified key"

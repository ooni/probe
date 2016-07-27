# -*- coding: utf-8 -*-
import os
import csv
import json

from copy import deepcopy

import yaml

from twisted.internet import defer
from twisted.python.filepath import FilePath

from ooni import constants
from ooni import errors as e
from ooni.backend_client import CollectorClient, BouncerClient
from ooni.backend_client import WebConnectivityClient, guess_backend_type
from ooni.nettest import NetTestLoader
from ooni.otime import timestampNowISO8601UTC
from ooni.resources import check_for_update
from ooni.settings import config
from ooni.utils import generate_filename
from ooni.utils import log
from ooni.geoip import probe_ip

from ooni.results import generate_summary

def nettest_to_path(path, allow_arbitrary_paths=False):
    """
    Takes as input either a path or a nettest name.

    The nettest name may either be prefixed by the category of the nettest (
    blocking, experimental, manipulation or third_party) or not.

    Args:

        allow_arbitrary_paths:
            allow also paths that are not relative to the nettest_directory.

    Returns:

        full path to the nettest file.
    """
    if allow_arbitrary_paths and os.path.exists(path):
        return path

    test_name = path.rsplit("/", 1)[-1]
    test_categories = [
        "blocking",
        "experimental",
        "manipulation",
        "third_party"
    ]
    nettest_dir = FilePath(config.nettest_directory)
    found_path = None
    for category in test_categories:
        p = nettest_dir.preauthChild(os.path.join(category, test_name) + '.py')
        if p.exists():
            if found_path is not None:
                raise Exception("Found two tests named %s" % test_name)
            found_path = p.path

    if not found_path:
        raise e.NetTestNotFound(path)
    return found_path


def get_preferred_bouncer():
    preferred_backend = config.advanced.get(
        "preferred_backend", "onion"
    )
    bouncer_address = getattr(
        constants, "CANONICAL_BOUNCER_{0}".format(
            preferred_backend.upper()
        )
    )
    if preferred_backend == "cloudfront":
        return BouncerClient(
            settings={
                'address': bouncer_address[0],
                'front': bouncer_address[1],
                'type': 'cloudfront'
        })
    else:
        return BouncerClient(bouncer_address)

@defer.inlineCallbacks
def lookup_collector_and_test_helpers(net_test_loaders,
                                      bouncer,
                                      preferred_backend,
                                      no_collector=False):
    required_nettests = []

    requires_test_helpers = False
    requires_collector = False
    for net_test_loader in net_test_loaders:
        nettest = {
            'name': net_test_loader.testName,
            'version': net_test_loader.testVersion,
            'test-helpers': [],
            # XXX deprecate this very soon
            'input-hashes': []
        }
        if not net_test_loader.collector and not no_collector:
            requires_collector = True

        if len(net_test_loader.missingTestHelpers) > 0:
            requires_test_helpers = True
            nettest['test-helpers'] += map(lambda x: x[1],
                                           net_test_loader.missingTestHelpers)

        required_nettests.append(nettest)

    if not requires_test_helpers and not requires_collector:
        defer.returnValue(None)

    response = yield bouncer.lookupTestCollector(required_nettests)
    try:
        provided_net_tests = yield get_reachable_test_helpers_and_collectors(
            response['net-tests'], preferred_backend)
    except e.NoReachableCollectors:
        log.err("Could not find any reachable collector")
        raise
    except e.NoReachableTestHelpers:
        log.err("Could not find any reachable test helpers")
        raise

    def find_collector_and_test_helpers(test_name, test_version):
        # input_files = [u""+x['hash'] for x in input_files]
        for net_test in provided_net_tests:
            if net_test['name'] != test_name:
                continue
            if net_test['version'] != test_version:
                continue
            # XXX remove the notion of policies based on input file hashes
            # if set(net_test['input-hashes']) != set(input_files):
            #    continue
            return net_test['collector'], net_test['test-helpers']

    for net_test_loader in net_test_loaders:
        log.msg("Setting collector and test helpers for %s" %
                net_test_loader.testName)

        collector, test_helpers = \
            find_collector_and_test_helpers(
                test_name=net_test_loader.testName,
                test_version=net_test_loader.testVersion
                # input_files=net_test_loader.inputFiles
            )

        for option, name in net_test_loader.missingTestHelpers:
            test_helper_address_or_settings = test_helpers[name]
            net_test_loader.localOptions[option] = test_helper_address_or_settings
            net_test_loader.testHelpers[option] = test_helper_address_or_settings

        if not net_test_loader.collector and not no_collector:
            log.debug("Using collector {0}".format(collector))
            net_test_loader.collector = collector

@defer.inlineCallbacks
def get_reachable_test_helpers_and_collectors(net_tests, preferred_backend):
    for net_test in net_tests:
        primary_address = net_test['collector']
        alternate_addresses = net_test.get('collector-alternate', [])
        net_test['collector'] = yield get_reachable_collector(
            primary_address, alternate_addresses, preferred_backend)

        for test_helper_name, test_helper_address in net_test['test-helpers'].items():
             test_helper_alternate = \
                 net_test.get('test-helpers-alternate', {}).get(test_helper_name, [])
             net_test['test-helpers'][test_helper_name] = \
                        yield get_reachable_test_helper(test_helper_name,
                                                        test_helper_address,
                                                        test_helper_alternate,
                                                        preferred_backend)

    defer.returnValue(net_tests)

@defer.inlineCallbacks
def get_reachable_collector(collector_address, collector_alternate,
                            preferred_backend):
    # We prefer onion collector to https collector to cloudfront
    # collectors to plaintext collectors
    for collector_settings in sort_addresses_by_priority(
            collector_address,
            collector_alternate,
            preferred_backend):
        collector = CollectorClient(settings=collector_settings)
        if not collector.isSupported():
            log.err("Unsupported %s collector %s" % (
                        collector_settings['type'],
                        collector_settings['address']))
            continue
        reachable = yield collector.isReachable()
        if not reachable:
            log.err("Unreachable %s collector %s" % (
                        collector_settings['type'],
                        collector_settings['address']))
            continue
        defer.returnValue(collector)

    raise e.NoReachableCollectors


@defer.inlineCallbacks
def get_reachable_test_helper(test_helper_name, test_helper_address,
                              test_helper_alternate, preferred_backend):
    # For the moment we look for alternate addresses only of
    # web_connectivity test helpers.
    if test_helper_name == 'web-connectivity':
        for web_connectivity_settings in sort_addresses_by_priority(
                test_helper_address, test_helper_alternate,
                preferred_backend):
            web_connectivity_test_helper = WebConnectivityClient(
                settings=web_connectivity_settings)
            if not web_connectivity_test_helper.isSupported():
                log.err("Unsupported %s web_connectivity test_helper "
                        "%s" % (
                        web_connectivity_settings['type'],
                        web_connectivity_settings['address']
                ))
                continue
            reachable = yield web_connectivity_test_helper.isReachable()
            if not reachable:
                log.err("Unreachable %s web_connectivity test helper %s" % (
                    web_connectivity_settings['type'],
                    web_connectivity_settings['address']
                ))
                continue
            defer.returnValue(web_connectivity_settings)
        raise e.NoReachableTestHelpers
    else:
        defer.returnValue(test_helper_address.encode('ascii'))

def sort_addresses_by_priority(priority_address,
                               alternate_addresses,
                               preferred_backend):
    prioritised_addresses = []

    backend_type = guess_backend_type(priority_address)
    priority_address = {
        'address': priority_address,
        'type': backend_type
    }
    address_priority = ['onion', 'https', 'cloudfront', 'http']
    address_priority.remove(preferred_backend)
    address_priority.insert(0, preferred_backend)

    def filter_by_type(collectors, collector_type):
        return filter(lambda x: x['type'] == collector_type, collectors)

    if (priority_address['type'] != preferred_backend):
        valid_alternatives = filter_by_type(alternate_addresses,
                                            preferred_backend)
        if len(valid_alternatives) > 0:
            alternate_addresses += [priority_address]
            priority_address = valid_alternatives[0]
            alternate_addresses.remove(priority_address)

    prioritised_addresses += [priority_address]
    for address_type in address_priority:
        prioritised_addresses += filter_by_type(alternate_addresses,
                                                address_type)

    return prioritised_addresses


class InputNotFound(Exception):
    pass


class InputStore(object):
    def __init__(self):
        self.path = FilePath(config.inputs_directory)
        self.resources = FilePath(config.resources_directory)
        self._cache_stale = True
        self._cache = {}

    @defer.inlineCallbacks
    def update_url_lists(self, country_code):
        countries = ["global"]
        if country_code != "ZZ":
            countries.append(country_code)

        for cc in countries:
            in_file = self.resources.child("citizenlab-test-lists").child("{0}.csv".format(cc))
            if not in_file.exists():
                yield check_for_update(country_code)

            if not in_file.exists():
                continue

            # XXX maybe move this to some utility function.
            # It's duplicated in oonideckgen.
            data_fname = "citizenlab-test-lists_{0}.txt".format(cc)
            desc_fname = "citizenlab-test-lists_{0}.desc".format(cc)

            out_file = self.path.child("data").child(data_fname)
            out_fh = out_file.open('w')
            with in_file.open('r') as in_fh:
                csvreader = csv.reader(in_fh)
                csvreader.next()
                for row in csvreader:
                    out_fh.write("%s\n" % row[0])
            out_fh.close()

            desc_file = self.path.child("descriptors").child(desc_fname)
            with desc_file.open('w') as out_fh:
                if cc == "global":
                    name = "List of globally accessed websites"
                else:
                    # XXX resolve this to a human readable country name
                    country_name = cc
                    name = "List of websites for {0}".format(country_name)
                json.dump({
                    "name": name,
                    "filepath": out_file.path,
                    "last_updated": timestampNowISO8601UTC(),
                    "id": "citizenlab_{0}_urls".format(cc),
                    "type": "file/url"
                }, out_fh)
        self._cache_stale = True

    @defer.inlineCallbacks
    def create(self, country_code=None):
        # XXX This is a hax to avoid race conditions in testing because this
        #  object is a singleton and config can have a custom home directory
        #  passed at runtime.
        self.path = FilePath(config.inputs_directory)
        self.resources = FilePath(config.resources_directory)

        self.path.child("descriptors").makedirs(ignoreExistingDirectory=True)
        self.path.child("data").makedirs(ignoreExistingDirectory=True)
        yield self.update_url_lists(country_code)

    @defer.inlineCallbacks
    def update(self, country_code=None):
        # XXX why do we make a difference between create and update?
        yield self.create(country_code)

    def _update_cache(self):
        descs = self.path.child("descriptors")
        if not descs.exists():
            self._cache = {}
            return

        for fn in descs.listdir():
            with descs.child(fn).open("r") as in_fh:
                input_desc = json.load(in_fh)
                self._cache[input_desc.pop("id")] = input_desc
        self._cache_stale = False
        return

    def list(self):
        if self._cache_stale:
            self._update_cache()
        return self._cache

    def get(self, input_id):
        if self._cache_stale:
            self._update_cache()
        try:
            input_desc = self._cache[input_id]
        except KeyError:
            raise InputNotFound(input_id)
        return input_desc

    def getContent(self, input_id):
        input_desc = self.get(input_id)
        with open(input_desc["filepath"]) as fh:
            return fh.read()

class DeckStore(object):
    def __init__(self):
        self.path = FilePath(config.decks_directory)

    def update(self):
        pass

    def get(self):
        pass

def resolve_file_path(v, prepath=None):
    if v.startswith("$"):
        # This raises InputNotFound and we let it carry onto the caller
        return input_store.get(v[1:])["filepath"]
    elif prepath is not None and (not os.path.isabs(v)):
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

        self._skip = False

        self.id = ""

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

    def _get_option(self, name, task_data, default=None):
        try:
            return self.global_options[name]
        except KeyError:
            return task_data.pop(name,
                                 self.parent_metadata.get(name, default))

    def _load_ooni(self, task_data):
        required_keys = ["test_name"]
        for required_key in required_keys:
            if required_key not in task_data:
                raise MissingTaskDataKey(required_key)

        # This raises e.NetTestNotFound, we let it go onto the caller
        nettest_path = nettest_to_path(task_data.pop("test_name"),
                                       self._arbitrary_paths)

        annotations = self._get_option('annotations', task_data, {})
        collector_address = self._get_option('collector', task_data, None)

        try:
            self.output_path = self.global_options['reportfile']
        except KeyError:
            self.output_path = task_data.pop('reportfile', None)

        if task_data.get('no-collector', False):
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
            file_path = resolve_file_path(input_file['filename'], self.cwd)
            input_file['test_options'][input_file['key']] = file_path
        self.ooni['test_details'] = self.ooni['net_test_loader'].getTestDetails()
        self.id = generate_filename(self.ooni['test_details'])

    def setup(self):
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

class NotAnOption(Exception):
    pass

def subargs_to_options(subargs):
    options = {}

    def parse_option_name(arg):
        if arg.startswith("--"):
            return arg[2:]
        elif arg.startswith("-"):
            return arg[1:]
        raise NotAnOption

    subargs = iter(reversed(subargs))
    for subarg in subargs:
        try:
            value = subarg
            name = parse_option_name(subarg)
            options[name] = True
        except NotAnOption:
            try:
                name = parse_option_name(subargs.next())
                options[name] = value
            except StopIteration:
                break

    return options

def convert_legacy_deck(deck_data):
    """
    I take a legacy deck list and convert it to the new deck format.

    :param deck_data: in the legacy format
    :return: deck_data in the new format
    """
    assert isinstance(deck_data, list), "Legacy decks are lists"
    new_deck_data = {}
    new_deck_data["name"] = "Legacy deck"
    new_deck_data["description"] = "This is a legacy deck converted to the " \
                                   "new format"
    new_deck_data["bouncer"] = None
    new_deck_data["tasks"] = []
    for deck_item in deck_data:
        deck_task = {"ooni": {}}

        options = deck_item["options"]
        deck_task["ooni"]["test_name"] = options.pop("test_file")
        deck_task["ooni"]["annotations"] = options.pop("annotations", {})
        deck_task["ooni"]["collector"] = options.pop("collector", None)

        # XXX here we end up picking only the last not none bouncer_address
        bouncer_address = options.pop("bouncer", None)
        if bouncer_address is not None:
            new_deck_data["bouncer"] = bouncer_address

        subargs = options.pop("subargs", [])
        for name, value in subargs_to_options(subargs).items():
            deck_task["ooni"][name] = value

        for name, value in options.items():
            deck_task["ooni"][name] = value

        new_deck_data["tasks"].append(deck_task)

    return new_deck_data

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
        self.task_ids = []

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
            self.task_ids.append(deck_task.id)

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
        test_details = task.ooni["test_details"]

        report_filename = task.output_path
        if not task.output_path:
            measurement_id = task.id

            measurement_dir = self._measurement_path.child(measurement_id)
            measurement_dir.createDirectory()

            report_filename = measurement_dir.child("measurements.njson.progress").path
            pid_file = measurement_dir.child("running.pid")

            with pid_file.open('w') as out_file:
                out_file.write("{0}".format(os.getpid()))

        d = director.start_net_test_loader(
            net_test_loader,
            report_filename,
            collector_client=net_test_loader.collector,
            test_details=test_details
        )
        d.addCallback(self._measurement_completed, task)
        d.addErrback(self._measurement_failed, task)
        return d

    @defer.inlineCallbacks
    def setup(self):
        """
        This method needs to be called before you are able to run a deck.
        """
        for task in self._tasks:
            yield task.setup()
        self._is_setup = True

    @defer.inlineCallbacks
    def run(self, director):
        assert self._is_setup, "You must call setup() before you can run a " \
                               "deck"
        if self.requires_tor:
            yield director.start_tor()
        yield self.query_bouncer()
        for task in self._tasks:
            if task._skip is True:
                log.msg("Skipping running {0}".format(task.name))
                continue
            if task.type == "ooni":
                yield self._run_ooni_task(task, director)
        self._is_setup = False

input_store = InputStore()

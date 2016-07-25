# -*- coding: utf-8 -*-
import os
import csv
import json

from copy import deepcopy
from hashlib import sha256

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

from ooni.results import generate_summary

class InputFile(object):
    def __init__(self, input_hash, base_path=config.inputs_directory):
        self.id = input_hash
        cache_path = os.path.join(os.path.abspath(base_path), input_hash)
        self.cached_file = cache_path
        self.cached_descriptor = cache_path + '.desc'

    @property
    def descriptorCached(self):
        if os.path.exists(self.cached_descriptor):
            with open(self.cached_descriptor) as f:
                descriptor = json.load(f)
                self.load(descriptor)
            return True
        return False

    @property
    def fileCached(self):
        if os.path.exists(self.cached_file):
            try:
                self.verify()
            except AssertionError:
                log.err("The input %s failed validation."
                        "Going to consider it not cached." % self.id)
                return False
            return True
        return False

    def save(self):
        with open(self.cached_descriptor, 'w+') as f:
            json.dump({
                'name': self.name,
                'id': self.id,
                'version': self.version,
                'author': self.author,
                'date': self.date,
                'description': self.description
            }, f)

    def load(self, descriptor):
        self.name = descriptor['name']
        self.version = descriptor['version']
        self.author = descriptor['author']
        self.date = descriptor['date']
        self.description = descriptor['description']

    def verify(self):
        digest = os.path.basename(self.cached_file)
        with open(self.cached_file) as f:
            file_hash = sha256(f.read())
            assert file_hash.hexdigest() == digest


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

class Deck(InputFile):
    # this exists so we can mock it out in unittests
    _BouncerClient = BouncerClient
    _CollectorClient = CollectorClient

    def __init__(self, deck_hash=None,
                 bouncer=None,
                 decks_directory=config.decks_directory,
                 no_collector=False):
        self.id = deck_hash
        self.no_collector = no_collector

        self.preferred_backend = config.advanced.get(
            "preferred_backend", "onion"
        )
        if self.preferred_backend not in ["onion", "https", "cloudfront"]:
            raise e.InvalidPreferredBackend

        if bouncer is None:
            bouncer_address = getattr(
                constants, "CANONICAL_BOUNCER_{0}".format(
                    self.preferred_backend.upper()
                )
            )
            if self.preferred_backend == "cloudfront":
                self.bouncer = self._BouncerClient(settings={
                    'address': bouncer_address[0],
                    'front': bouncer_address[1],
                    'type': 'cloudfront'
                })
            else:
                self.bouncer = self._BouncerClient(bouncer_address)
        else:
            self.bouncer = self._BouncerClient(bouncer)

        self.requiresTor = False

        self.netTestLoaders = []
        self.inputs = []

        self.decksDirectory = os.path.abspath(decks_directory)

    @property
    def cached_file(self):
        return os.path.join(self.decksDirectory, self.id)

    @property
    def cached_descriptor(self):
        return self.cached_file + '.desc'

    def loadDeck(self, deckFile, global_options={}):
        with open(deckFile) as f:
            self.id = sha256(f.read()).hexdigest()
            f.seek(0)
            test_deck = yaml.safe_load(f)

        for test in test_deck:
            try:
                nettest_path = nettest_to_path(test['options']['test_file'])
            except e.NetTestNotFound:
                log.err("Could not find %s" % test['options']['test_file'])
                log.msg("Skipping...")
                continue

            annotations = test['options'].get('annotations', {})
            if global_options.get('annotations') is not None:
                annotations = global_options["annotations"]

            collector_address = test['options'].get('collector', None)
            if global_options.get('collector') is not None:
                collector_address = global_options['collector']

            net_test_loader = NetTestLoader(test['options']['subargs'],
                                            annotations=annotations,
                                            test_file=nettest_path)
            if collector_address is not None:
                net_test_loader.collector = CollectorClient(
                    collector_address
                )
            if test['options'].get('bouncer', None) is not None:
                self.bouncer = self._BouncerClient(test['options']['bouncer'])
                if self.bouncer.backend_type is "onion":
                    self.requiresTor = True
            self.insert(net_test_loader)

    def insert(self, net_test_loader):
        """ Add a NetTestLoader to this test deck """
        if (net_test_loader.collector is not None
                and net_test_loader.collector.backend_type is "onion"):
            self.requiresTor = True
        try:
            net_test_loader.checkOptions()
            if net_test_loader.requiresTor:
                self.requiresTor = True
        except e.MissingTestHelper:
            if self.preferred_backend is "onion":
                self.requiresTor = True

        self.netTestLoaders.append(net_test_loader)

    @defer.inlineCallbacks
    def setup(self):
        """ fetch and verify inputs for all NetTests in the deck """
        log.msg("Fetching required net test inputs...")
        for net_test_loader in self.netTestLoaders:
            # XXX figure out if we want to keep this or drop this.
            yield self.fetchAndVerifyNetTestInput(net_test_loader)

        if self.bouncer:
            log.msg("Looking up collector and test helpers with {0}".format(
                self.bouncer.base_address))
            yield lookup_collector_and_test_helpers(self.netTestLoaders,
                                                    self.bouncer,
                                                    self.preferred_backend,
                                                    self.no_collector)

    @defer.inlineCallbacks
    def fetchAndVerifyNetTestInput(self, net_test_loader):
        """ fetch and verify a single NetTest's inputs """
        log.debug("Fetching and verifying inputs")
        for i in net_test_loader.inputFiles:
            if i['url']:
                log.debug("Downloading %s" % i['url'])
                oonibclient = self._CollectorClient(i['address'])

                try:
                    input_file = yield oonibclient.downloadInput(i['hash'])
                except:
                    raise e.UnableToLoadDeckInput

                try:
                    input_file.verify()
                except AssertionError:
                    raise e.UnableToLoadDeckInput

                i['test_options'][i['key']] = input_file.cached_file


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
            'input-hashes': [x['hash'] for x in net_test_loader.inputFiles]
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

    def find_collector_and_test_helpers(test_name, test_version, input_files):
        input_files = [u""+x['hash'] for x in input_files]
        for net_test in provided_net_tests:
            if net_test['name'] != test_name:
                continue
            if net_test['version'] != test_version:
                continue
            if set(net_test['input-hashes']) != set(input_files):
                continue
            return net_test['collector'], net_test['test-helpers']

    for net_test_loader in net_test_loaders:
        log.msg("Setting collector and test helpers for %s" %
                net_test_loader.testName)

        collector, test_helpers = \
            find_collector_and_test_helpers(test_name=net_test_loader.testName,
                                            test_version=net_test_loader.testVersion,
                                            input_files=net_test_loader.inputFiles)

        for option, name in net_test_loader.missingTestHelpers:
            test_helper_address_or_settings = test_helpers[name]
            net_test_loader.localOptions[option] = test_helper_address_or_settings
            net_test_loader.testHelpers[option] = test_helper_address_or_settings

        if not net_test_loader.collector:
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

def options_to_args(options, prepath=None):
    args = []
    for k, v in options.items():
        if v is None:
            continue
        if k == "file":
            v = resolve_file_path(v, prepath)
        args.append('--'+k)
        args.append(v)
    return args

class UnknownTaskKey(Exception):
    pass

class MissingTaskDataKey(Exception):
    pass

class DeckTask(object):
    _metadata_keys = ["name"]
    _supported_tasks = ["ooni"]

    def __init__(self, data, parent_metadata={}, cwd=None):
        self.parent_metadata = parent_metadata
        self.cwd = cwd
        self.data = deepcopy(data)

        self.id = ""

        self.type = None
        self.metadata = {}
        self.requires_tor = False
        self.requires_bouncer = False

        self.ooni = {
            'bouncer_client': None,
            'test_details': {}
        }

        self._load(data)

    def _load_ooni(self, task_data):
        required_keys = ["test_name"]
        for required_key in required_keys:
            if required_key not in task_data:
                raise MissingTaskDataKey(required_key)

        # This raises e.NetTestNotFound, we let it go onto the caller
        nettest_path = nettest_to_path(task_data.pop("test_name"))

        try:
            annotations = task_data.pop('annotations')
        except KeyError:
            annotations = self.parent_metadata.get('annotations', {})

        try:
            collector_address = task_data.pop('collector')
        except KeyError:
            collector_address = self.parent_metadata.get('collector', None)

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
        # Need to ensure that this is called only once we have looked up the
        #  probe IP address and have geoip data.
        self.ooni['test_details'] = net_test_loader.getTestDetails()
        self.id = generate_filename(self.ooni['test_details'])

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

        assert len(data) == 0

class NGDeck(object):
    def __init__(self, deck_data=None,
                 deck_path=None, no_collector=False):
        # Used to resolve relative paths inside of decks.
        self.deck_directory = None
        self.requires_tor = False
        self.no_collector = no_collector
        self.name = ""
        self.description = ""
        self.schedule = None

        self.metadata = {}
        self.bouncer = None

        self._measurement_path = FilePath(config.measurements_directory)
        self._tasks = []
        self.task_ids = []

        if deck_path is not None:
            self.open(deck_path)
        elif deck_data is not None:
            self.load(deck_data)

    def open(self, deck_path):
        with open(deck_path) as fh:
            deck_data = yaml.safe_load(fh)
        self.load(deck_data)

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

    def load(self, deck_data):
        self.name = deck_data.pop("name", "Un-named Deck")
        self.description = deck_data.pop("description", "No description")

        bouncer_address = deck_data.pop("bouncer", None)
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

        for task_data in tasks_data:
            deck_task = DeckTask(task_data, self.metadata, self.deck_directory)
            if deck_task.requires_tor:
                self.requires_tor = True
            if (deck_task.requires_bouncer and
                    self.bouncer.backend_type == "onion"):
                self.requires_tor = True
            self._tasks.append(deck_task)
            self.task_ids.append(deck_task.id)

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

    def _measurement_completed(self, result, measurement_id):
        log.msg("{0}".format(result))
        measurement_dir = self._measurement_path.child(measurement_id)
        measurement_dir.child("measurements.njson.progress").moveTo(
            measurement_dir.child("measurements.njson")
        )
        generate_summary(
            measurement_dir.child("measurements.njson").path,
            measurement_dir.child("summary.json").path
        )
        measurement_dir.child("running.pid").remove()

    def _measurement_failed(self, failure, measurement_id):
        measurement_dir = self._measurement_path.child(measurement_id)
        measurement_dir.child("running.pid").remove()
        # XXX do we also want to delete measurements.njson.progress?
        return failure

    def _run_ooni_task(self, task, director):
        net_test_loader = task.ooni["net_test_loader"]
        test_details = task.ooni["test_details"]
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
            test_details=test_details
        )
        d.addCallback(self._measurement_completed, measurement_id)
        d.addErrback(self._measurement_failed, measurement_id)
        return d

    @defer.inlineCallbacks
    def run(self, director):
        tasks = []
        preferred_backend = config.advanced.get("preferred_backend", "onion")
        yield self.query_bouncer()
        for task in self._tasks:
            if task.requires_tor:
                yield director.start_tor()
            elif task.requires_bouncer and preferred_backend == "onion":
                yield director.start_tor()
            if task.type == "ooni":
                tasks.append(self._run_ooni_task(task, director))
        defer.returnValue(tasks)

input_store = InputStore()

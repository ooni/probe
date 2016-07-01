# -*- coding: utf-8 -*-

from ooni.backend_client import CollectorClient, BouncerClient
from ooni.backend_client import WebConnectivityClient, guess_backend_type
from ooni.nettest import NetTestLoader
from ooni.settings import config
from ooni.utils import log, onion
from ooni import constants
from ooni import errors as e

from twisted.python.filepath import FilePath
from twisted.internet import defer

import os
import yaml
import json
from hashlib import sha256


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
            yield self.lookupCollectorAndTestHelpers()


    def sortAddressesByPriority(self, priority_address, alternate_addresses):
        prioritised_addresses = []

        backend_type = guess_backend_type(priority_address)
        priority_address = {
            'address': priority_address,
            'type': backend_type
        }
        address_priority = ['onion', 'https', 'cloudfront', 'http']
        address_priority.remove(self.preferred_backend)
        address_priority.insert(0, self.preferred_backend)

        def filter_by_type(collectors, collector_type):
            return filter(lambda x: x['type'] == collector_type, collectors)

        if (priority_address['type'] != self.preferred_backend):
            valid_alternatives = filter_by_type(alternate_addresses,
                                                self.preferred_backend)
            if len(valid_alternatives) > 0:
                alternate_addresses += [priority_address]
                priority_address = valid_alternatives[0]
                alternate_addresses.remove(priority_address)

        prioritised_addresses += [priority_address]
        for address_type in address_priority:
            prioritised_addresses += filter_by_type(alternate_addresses,
                                                    address_type)

        return prioritised_addresses

    @defer.inlineCallbacks
    def getReachableCollector(self, collector_address, collector_alternate):
        # We prefer onion collector to https collector to cloudfront
        # collectors to plaintext collectors
        for collector_settings in self.sortAddressesByPriority(collector_address,
                                                               collector_alternate):
            collector = self._CollectorClient(settings=collector_settings)
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
    def getReachableTestHelper(self, test_helper_name, test_helper_address,
                               test_helper_alternate):
        # For the moment we look for alternate addresses only of
        # web_connectivity test helpers.
        if test_helper_name == 'web-connectivity':
            for web_connectivity_settings in self.sortAddressesByPriority(
                    test_helper_address, test_helper_alternate):
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

    @defer.inlineCallbacks
    def getReachableTestHelpersAndCollectors(self, net_tests):
        for net_test in net_tests:

            primary_address = net_test['collector']
            alternate_addresses = net_test.get('collector-alternate', [])
            net_test['collector'] = yield self.getReachableCollector(
                        primary_address,
                        alternate_addresses
            )

            for test_helper_name, test_helper_address in net_test['test-helpers'].items():
                 test_helper_alternate = \
                     net_test.get('test-helpers-alternate', {}).get(test_helper_name, [])
                 net_test['test-helpers'][test_helper_name] = \
                            yield self.getReachableTestHelper(
                                test_helper_name,
                                test_helper_address,
                                test_helper_alternate)

        defer.returnValue(net_tests)

    @defer.inlineCallbacks
    def lookupCollectorAndTestHelpers(self):
        required_nettests = []

        requires_test_helpers = False
        requires_collector = False
        for net_test_loader in self.netTestLoaders:
            nettest = {
                'name': net_test_loader.testName,
                'version': net_test_loader.testVersion,
                'test-helpers': [],
                'input-hashes': [x['hash'] for x in net_test_loader.inputFiles]
            }
            if not net_test_loader.collector and not self.no_collector:
                requires_collector = True

            if len(net_test_loader.missingTestHelpers) > 0:
                requires_test_helpers = True
                nettest['test-helpers'] += map(lambda x: x[1],
                                               net_test_loader.missingTestHelpers)

            required_nettests.append(nettest)

        if not requires_test_helpers and not requires_collector:
            defer.returnValue(None)

        response = yield self.bouncer.lookupTestCollector(required_nettests)
        try:
            provided_net_tests = yield self.getReachableTestHelpersAndCollectors(response['net-tests'])
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

        for net_test_loader in self.netTestLoaders:
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

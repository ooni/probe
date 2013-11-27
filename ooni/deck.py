#-*- coding: utf-8 -*-

from ooni.nettest import NetTestLoader
from ooni.settings import config
from ooni.utils import log
from ooni import errors as e

from twisted.internet import reactor, defer

import os
import re
import yaml
import json
from hashlib import sha256

class InputFile(object):
    def __init__(self, input_hash):
        self.id = input_hash
        cached_input_dir = os.path.join(config.advanced.data_dir,
                'inputs')
        cache_path = os.path.join(cached_input_dir, input_hash)
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
                log.err("The input %s failed validation. Going to consider it not cached." % self.id)
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

def nettest_to_path(path):
    """
    Takes as input either a path or a nettest name.
    
    Returns:

        full path to the nettest file.
    """
    path_via_name = os.path.join(config.nettest_directory, path + '.py')
    if os.path.exists(path):
        return path
    elif os.path.exists(path_via_name):
        return path_via_name
    else:
        raise e.NetTestNotFound(path)

class Deck(InputFile):
    def __init__(self, deck_hash=None, deckFile=None):
        self.id = deck_hash
        self.bouncer = None
        self.netTestLoaders = []
        self.inputs = []
        self.testHelpers = {}

        self.deckHash = deck_hash
 
        if deckFile: self.loadDeck(deckFile)

    @property
    def cached_file(self):
        cached_deck_dir = os.path.join(config.advanced.data_dir, 'decks')
        return os.path.join(cached_deck_dir, self.deckHash)
   
    @property
    def cached_descriptor(self):
        return self.cached_file + '.desc'

    def loadDeck(self, deckFile):
        with open(deckFile) as f:
            self.deckHash = sha256(f.read())
            f.seek(0)
            test_deck = yaml.safe_load(f)

        for test in test_deck:
            try:
                nettest_path = nettest_to_path(test['options']['test_file'])
            except e.NetTestNotFound:
                log.err("Could not find %s" % test['options']['test_file'])
                log.msg("Skipping...")
                continue
            net_test_loader = NetTestLoader(test['options']['subargs'],
                    test_file=nettest_path)
            self.insert(net_test_loader)
            #XXX: If the deck specifies the collector, we use the specified collector
            # And it should also specify the test helper address to use
            # net_test_loader.collector = test['options']['collector']

    def insert(self, net_test_loader):
        """ Add a NetTestLoader to this test deck """
        try:
            net_test_loader.checkOptions()
        except e.MissingRequiredOption, option_name:
            if not self.bouncer:
                raise
            for rth in net_test_loader.requiredTestHelpers:
                if option_name.message == rth['option']:
                    break
            else:
                raise
        self.netTestLoaders.append(net_test_loader)

    @defer.inlineCallbacks
    def setup(self):
        """ fetch and verify inputs for all NetTests in the deck """
        for net_test_loader in self.netTestLoaders:
            log.msg("Fetching required net test inputs...")
            yield self.fetchAndVerifyNetTestInput(net_test_loader)

        if self.bouncer:
            log.msg("Looking up test helpers...")
            yield self.lookupTestHelpers()
    
    @defer.inlineCallbacks
    def lookupTestHelpers(self):
        from ooni.oonibclient import OONIBClient
        oonibclient = OONIBClient(self.bouncer)
        required_test_helpers = []
        requires_collector = []
        for net_test_loader in self.netTestLoaders:
            if not net_test_loader.collector:
                requires_collector.append(net_test_loader)

            for th in net_test_loader.requiredTestHelpers:
                # {'name':'', 'option':'', 'test_class':''}
                if th['test_class'].localOptions[th['option']]:
                    continue
                required_test_helpers.append(th['name'])
        
        if not required_test_helpers and not requires_collector:
            defer.returnValue(None)

        response = yield oonibclient.lookupTestHelpers(required_test_helpers)

        for net_test_loader in self.netTestLoaders:
            log.msg("Setting collector and test helpers for %s" % net_test_loader.testDetails['test_name'])

            # Only set the collector if the no collector has been specified
            # from the command line or via the test deck.
            if not required_test_helpers and net_test_loader in requires_collector:
                log.msg("Using the default collector: %s" % response['default']['collector'])
                net_test_loader.collector = response['default']['collector'].encode('utf-8')
                continue

            for th in net_test_loader.requiredTestHelpers:
                # Only set helpers which are not already specified
                if th['name'] not in required_test_helpers:
                    continue
                test_helper = response[th['name']]
                log.msg("Using this helper: %s" % test_helper)
                th['test_class'].localOptions[th['option']] = test_helper['address'].encode('utf-8')
                if net_test_loader in requires_collector:
                    net_test_loader.collector = test_helper['collector'].encode('utf-8')

    @defer.inlineCallbacks
    def fetchAndVerifyNetTestInput(self, net_test_loader):
        """ fetch and verify a single NetTest's inputs """
        from ooni.oonibclient import OONIBClient
        log.debug("Fetching and verifying inputs")
        for i in net_test_loader.inputFiles:
            if 'url' in i:
                log.debug("Downloading %s" % i['url'])
                oonibclient = OONIBClient(i['address'])
                
                try:
                    input_file = yield oonibclient.downloadInput(i['hash'])
                except:
                    raise e.UnableToLoadDeckInput

                try:
                    input_file.verify()
                except AssertionError:
                    raise e.UnableToLoadDeckInput, cached_path
                
                i['test_class'].localOptions[i['key']] = input_file.cached_file

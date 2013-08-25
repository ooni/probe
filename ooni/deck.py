#-*- coding: utf-8 -*-

from ooni.nettest import NetTestLoader
from ooni.settings import config
from ooni.utils import log
from ooni.utils.txagentwithsocks import Agent
from ooni import errors as e
from ooni.oonibclient import OONIBClient

from twisted.internet import reactor, defer

import os
import re
import yaml

class Deck(object):
    def __init__(self, bouncer, deckFile=None):
        self.bouncer = bouncer
        self.netTestLoaders = []
        self.inputs = []
        self.testHelpers = {}
        self.collector = None

        if deckFile: self.loadDeck(deckFile)

    def loadDeck(self, deckFile):
        test_deck = yaml.safe_load(open(deckFile))
        for test in test_deck:
            net_test_loader = NetTestLoader(test['options']['subargs'],
                    test_file=test['options']['test_file'])
            net_test_loader.checkOptions()
            self.netTestLoaders.append(net_test_loader)

    def insert(self, net_test_loader):
        """ Add a NetTestLoader to this test deck """
        net_test_loader.checkOptions()
        self.netTestLoaders.append(net_test_loader)

    def getRequiredTestHelpers(self):
        for net_test_loader in self.netTestLoaders:
            for test_helper in net_test_loader.requiredTestHelpers:
                self.testHelpers[test_helper['name']] = None
    
    @defer.inlineCallbacks
    def setup(self):
        """ fetch and verify inputs for all NetTests in the deck """
        for net_test_loader in self.netTestLoaders:
            yield self.fetchAndVerifyNetTestInput(net_test_loader)
        self.getRequiredTestHelpers()
        yield self.lookupTestHelpers()

    @defer.inlineCallbacks
    def fetchAndVerifyNetTestInput(self, net_test_loader):
        """ fetch and verify a single NetTest's inputs """
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

    def setNettestOptions(self):
        for net_test_loader in self.netTestLoaders:
            for th in net_test_loader.requiredTestHelpers:
                test_helper_address = self.testHelpers[th['name']]
                th['test_class'].localOptions[th['option']] = test_helper_address
                net_test_loader.collector = self.collector
                log.debug("Using %s: %s" % (test_helper_address, self.collector)) 

    @defer.inlineCallbacks
    def lookupTestHelpers(self):
        log.msg("Looking up test helpers: %s" % self.testHelpers.keys())
        
        required_test_helpers = self.testHelpers.keys()
        if required_test_helpers: 
            oonibclient = OONIBClient(self.bouncer)
            test_helpers = yield oonibclient.lookupTestHelpers(required_test_helpers)
            self.collector = test_helpers['collector']
            for name in self.testHelpers.keys():
                self.testHelpers[name] = test_helpers[name]
            self.setNettestOptions()

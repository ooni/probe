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
        if deckFile: self.loadDeck(deckFile)

    def loadDeck(self, deckFile):
        test_deck = yaml.safe_load(open(deckFile))
        for test in test_deck:
            net_test_loader = NetTestLoader(test['options']['subargs'],
                    test_file=test['options']['test_file'])
            #XXX: If the deck specifies the collector, we use the specified collector
            # And it should also specify the test helper address to use
            # net_test_loader.collector = test['options']['collector']
            net_test_loader.checkOptions()
            self.netTestLoaders.append(net_test_loader)

    def insert(self, net_test_loader):
        """ Add a NetTestLoader to this test deck """
        net_test_loader.checkOptions()
        self.netTestLoaders.append(net_test_loader)

    @defer.inlineCallbacks
    def setup(self):
        """ fetch and verify inputs for all NetTests in the deck """
        for net_test_loader in self.netTestLoaders:
            yield self.fetchAndVerifyNetTestInput(net_test_loader)
            yield self.lookupTestHelper(net_test_loader)
            yield self.lookupTestCollector(net_test_loader)

    @defer.inlineCallbacks
    def lookupTestHelper(self, net_test_loader):
        oonibclient = OONIBClient(self.bouncer)
        for th in net_test_loader.requiredTestHelpers:
            # {'name':'', 'option':'', 'test_class':''}
            helper = yield oonibclient.lookupTestHelper(th['name'])
            th['test_class'].localOptions[th['option']] = helper['test-helper']
            #XXX: collector is only set once!
            net_test_loader.collector = helper['collector']


    @defer.inlineCallbacks
    def lookupTestCollector(self, net_test_loader):
        oonibclient = OONIBClient(self.bouncer)
        if net_test_loader.collector is None:
            net_test_loader.collector = oonibclient.lookupTestCollector(th['test_class'].testName)

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

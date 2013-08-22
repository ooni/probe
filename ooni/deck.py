#-*- coding: utf-8 -*-

from ooni.nettest import NetTestLoader
from ooni.settings import config
from ooni.utils import log
from ooni.utils.txagentwithsocks import Agent
from ooni.errors import UnableToLoadDeckInput
from ooni.oonibclient import OONIBClient

from twisted.internet import reactor, defer

import os
import re
import yaml

class Deck(object):
    def __init__(self, deckFile=None):
        self.netTestLoaders = []
        self.inputs = []

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
        self.fetchAndVerifyNetTestInput(net_test_loader)
        self.netTestLoaders.append(net_test_loader)
 
    @defer.inlineCallbacks
    def fetchAndVerifyDeckInputs(self):
        """ fetch and verify inputs for all NetTests in the deck """
        for net_test_loader in self.netTestLoaders:
            yield self.fetchAndVerifyNetTestInput(net_test_loader)

    @defer.inlineCallbacks
    def fetchAndVerifyNetTestInput(self, net_test_loader):
        """ fetch and verify a single NetTest's inputs """
        log.debug("Fetching and verifying inputs")
        for i in net_test_loader.inputFiles:
            if 'url' in i:
                log.debug("Downloading %s" % i['url'])
                oonib = OONIBClient(i['address'])

                input_file = yield oonib.downloadInput(i['hash'])
                try:
                    input_file.verify()
                except AssertionError:
                    raise UnableToLoadDeckInput, cached_path
                
                i['test_class'].localOptions[i['key']] = input_file.cached_file

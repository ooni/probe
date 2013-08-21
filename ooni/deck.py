#-*- coding: utf-8 -*-

from hashlib import sha1
from ooni.nettest import NetTestLoader
from ooni.settings import config
from ooni.utils.txagentwithsocks import Agent
from ooni.errors import UnableToLoadDeckInput
from twisted.internet import reactor, defer
import os
import re
import yaml

def verifyFile(filePath):
    # get the filename component of the file path
    digest = os.path.basename(filePath)
    with open(filePath) as f:
        sha1digest = sha1(f.read())
        return sha1digest.hexdigest() == digest
    return False

class Deck(object):
    def __init__(self, oonibclient, deckFile=None):
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
 
    def fetchAndVerifyDeckInputs(self):
        """ fetch and verify inputs for all NetTests in the deck """
        for net_test_loader in self.netTestLoaders:
            self.fetchAndVerifyNetTestInput(net_test_loader)

    @defer.inlineCallbacks
    def fetchAndVerifyNetTestInput(self, net_test_loader):
        """ fetch and verify a single NetTest's inputs """
        for input_file in net_test_loader.inputFiles:
            if 'url' in input_file:
                oonib = OONIBClient(input_file['address'])

                cached_input_dir = os.path.join(config.advanced.data_dir,
                        'inputs')
                cached_path = os.path.join(cached_input_dir, input_file['hash'])
                self.inputs.append(cached_path)

                if os.path.exists(cached_path) and verifyFile(cached_path):
                        test_class.localOptions[inputArg] = cached_path
                        continue
                yield oonib.downloadInput(input_file['hash'], cached_path)
                if verifyFile(cached_path):
                    test_class.localOptions[input_file['key']] = cached_path
                    continue
                
                raise UnableToLoadDeckInput, cached_path

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

onionInputRegex =  re.compile("httpo://[a-z0-9]{16}\.onion/input/([a-z0-9]){40}$")

@defer.inlineCallbacks
def downloadFile(fileURL, filePath):

    def writeFile(response_body, filePath): 
        f = open(filePath, 'w+')
        f.write(response_body)

    finished = defer.Deferred()
    finished.addCallback(writeFile, filePath)

    agent = Agent(reactor, sockshost="127.0.0.1",
            socksport=int(config.tor.socks_port))
    response = yield agent.request("GET", fileURL)
    response.deliverBody(BodyReceiver(finished))

def verifyFile(filePath):
    # get the filename component of the file path
    digest = os.path.basename(filePath)
    with open(filePath) as f:
        sha1digest = sha1(f.read())
        return sha1digest.hexdigest() == digest
    return False

class TestDeck(object):
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
 
    def fetchAndVerifyDeckInputs(self):
        """ fetch and verify inputs for all NetTests in the deck """
        for net_test_loader in self.netTestLoaders:
            self.fetchAndVerifyNetTestInput(net_test_loader)

    @defer.inlineCallbacks
    def fetchAndVerifyNetTestInput(self, net_test_loader):
        """ fetch and verify a single NetTest's inputs """
        for test_class, test_methods in net_test_loader.testCases:
            if test_class.inputFile:
                inputArg = test_class.inputFile[0]
                inputFileURL = test_class.localOptions[inputArg]
    
                m = onionInputRegex.match(inputFileURL)
                if m:
                    fileDigest = m.group(1)
                else:
                    fileDigest = os.path.basename(inputFileURL)

                cachedInputDir = os.path.join(config.advanced.data_dir,
                        'inputs')
                cachedPath = os.path.join(cachedInputDir, fileDigest)
                self.inputs.append(cachedPath)

                if os.path.exists(cachedPath) and verifyFile(cachedPath):
                        test_class.localOptions[inputArg] = cachedPath
                        continue
                if m:
                    yield downloadFile(inputFileURL, cachedPath)
                    if verifyFile(cachedPath):
                        test_class.localOptions[inputArg] = cachedPath
                        continue

                raise UnableToLoadDeckInput, cachedPath

def test_verify_file_success(): 
    f = open('/dev/urandom')
    r = f.read(1024*1024)
    z = sha1(f).hexdigest()
    f.close()
    fn = '/tmp/%s' % z
    f = open(fn)
    f.write(r)
    f.close()
    verifyFile(fn)
    os.unlink(fn)

def test_verify_file_failure():
    pass
def test_load_deck_with_no_inputs(deck):
    pass
def test_load_deck_with_cached_input(deckFile):
    pass
def test_load_deck_with_evil_path(deckFile):
    pass
def test_load_deck_with_download_success(deckFile):
    pass
def test_load_deck_with_download_failure(deckFile):
    pass

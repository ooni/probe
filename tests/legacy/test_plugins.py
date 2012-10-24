from twisted.internet import defer, reactor
from twisted.trial import unittest

from ooni.ooniprobe import retrieve_plugoo, runTest, Options
from ooni.plugoo import work, tests

def asset_file(filename):
    import os
    file_dir = os.path.normpath(os.path.join(__file__, '..'))
    return os.path.join(file_dir, 'assets', filename)

class PluginsTestCase(unittest.TestCase):
    def test_plugin_blocking(self):
        suboptions = {'asset': asset_file('urllist.txt')}
        runTest('blocking', suboptions, Options(), reactor)
        return

    def test_plugin_tcpconnect(self):
        suboptions = {'asset': asset_file('ipports.txt')}
        runTest('tcpconnect', suboptions, Options(), reactor)
        return


    def test_plugin_captivep(self):
        runTest('blocking', None, Options(), reactor)
        return


    def test_plugin_httphost(self):
        suboptions = {'asset': asset_file('urllist.txt')}
        runTest('httphost', suboptions, Options(), reactor)
        return


    def test_plugin_httpt(self):
        suboptions = {'urls': asset_file('urllist.txt')}
        runTest('httpt', suboptions, Options(), reactor)
        return



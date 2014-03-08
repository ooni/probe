# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage

from ooni.templates import httpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', 'http://127.0.0.1:57001',
                        'URL of the test backend to use']]

class HTTPKeywordFiltering(httpt.HTTPTest):
    """
    This test involves performing HTTP requests containing to be tested for
    censorship keywords.

    It does not detect censorship on the client, but just logs the response from the 
    HTTP backend server.
    """
    name = "HTTP Keyword Filtering"
    author = "Arturo Filastò"
    version = "0.1.1"

    inputFile = ['file', 'f', None, 'List of keywords to use for censorship testing']

    usageOptions = UsageOptions
    requiresTor = False
    requiresRoot = False

    requiredOptions = ['backend']

    def test_get(self):
        """
        Perform a HTTP GET request to the backend containing the keyword to be
        tested inside of the request body.
        """
        return self.doRequest(self.localOptions['backend'], method="GET", body=self.input)

    def test_post(self):
        """
        Perform a HTTP POST request to the backend containing the keyword to be
        tested inside of the request body.
        """
        return self.doRequest(self.localOptions['backend'], method="POST", body=self.input)


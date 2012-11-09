# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.templates import httpt
class HTTPKeywordFiltering(httpt.HTTPTest):
    """
    This test involves performing HTTP requests containing to be tested for
    censorship keywords.

    It does not detect censorship on the client, but just logs the response from the 
    HTTP backend server.
    """
    name = "HTTP Keyword Filtering"
    author = "Arturo Filastò"
    version = 0.1

    optParameters = [['backend', 'b', None, 'URL of the backend system to use for testing']]

    inputFile = ['file', 'f', None, 'List of keywords to use for censorship testing']

    def processInputs(self):
        if 'backend' in self.localOptions:
            self.url = self.localOptions['backend']
        else:
            raise Exception("No backend specified")

    def test_get(self):
        """
        Perform a HTTP GET request to the backend containing the keyword to be
        tested inside of the request body.
        """
        return self.doRequest(self.url, method="GET", body=self.input)

    def test_post(self):
        """
        Perform a HTTP POST request to the backend containing the keyword to be
        tested inside of the request body.
        """
        return self.doRequest(self.url, method="POST", body=self.input)


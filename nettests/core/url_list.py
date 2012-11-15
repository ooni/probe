# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage
from ooni.templates import httpt

class UsageOptions(usage.Options):
    optParameters = [['content', 'c', None,
                        'The file to read from containing the content of a block page'],
                     ['url', 'u', None, 'Specify a single URL to test.']
                    ]

class URLList(httpt.HTTPTest):
    """
    Performs GET, POST and PUT requests to a list of URLs specified as
    input and checks if the page that we get back as a result matches that
    which we expect.
    """
    name = "URL List"
    author = "Arturo Filastò"
    version = "0.1.2"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, 
            'List of URLS to perform GET and POST requests to']

    def setUp(self):
        """
        Check for inputs.
        """
        if self.input:
            self.url = self.input
        elif self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            raise Exception("No input specified")

    def check_for_censorship(self, body):
        """
        If we have specified what a censorship page looks like here we will
        check if the page we are looking at matches it.

        XXX this is not tested, though it is basically what was used to detect
        censorship in the palestine case.
        """
        if self.localOptions['content']:
            self.report['censored'] = True

            censorship_page = open(self.localOptions['content'])
            response_page = iter(body.split("\n"))

            for censorship_line in censorship_page.xreadlines():
                response_line = response_page.next()
                if response_line != censorship_line:
                    self.report['censored'] = False
                    break
            censorship_page.close()

    def test_get(self):
        return self.doRequest(self.url, method="GET")

    def test_post(self):
        return self.doRequest(self.url, method="POST")

    def test_put(self):
        return self.doRequest(self.url, method="PUT")



# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.templates import httpt

class URLList(httpt.HTTPTest):
    name = "URL List"
    author = "Arturo Filastò"
    version = 0.1

    inputFile = ['file', 'f', None, 'List of URLS to perform GET and POST requests to']
    
    requiredOptions = ['file']
    def test_get(self):
        if self.input:
            self.url = self.input
        else:
            raise Exception("No input specified")

        return self.doRequest(self.url)



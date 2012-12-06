# -*- encoding: utf-8 -*-
#
# :authors: Aaron Gibson
# :licence: see LICENSE

from ooni.utils import log
from ooni.templates import httpt
from hashlib import sha256

class SHA256HTTPBodyTest(httpt.HTTPTest):
    name = "ChecksumHTTPBodyTest"
    author = "Aaron Gibson"
    version = 0.1

    inputFile = ['file', 'f', None, 
            'List of URLS to perform GET requests to']

    def test_http(self):
        if self.input:
            url = self.input
            return self.doRequest(url)
        else:
            raise Exception("No input specified")

    def processResponseBody(self, body):
        body_sha256sum = sha256(body).digest()
        self.report['checksum'] = body_sha256sum

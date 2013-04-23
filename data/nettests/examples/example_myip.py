# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.templates import httpt
class MyIP(httpt.HTTPTest):
    inputs = ['https://check.torproject.org']

    def test_lookup(self):
        return self.doRequest(self.input)

    def processResponseBody(self, body):
        import re
        regexp = "Your IP address appears to be: <b>(.+?)<\/b>"
        match = re.search(regexp, body)
        try:
            self.report['myip'] = match.group(1)
        except:
            self.report['myip'] = None


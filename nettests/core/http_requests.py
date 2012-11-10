# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from ooni.templates import httpt

def random_capitalization(string):
    output = ""
    string = string.swapcase()
    for i in range(len(string)):
        if random.randint(0, 1):
            output += string[i].swapcase()
        else:
            output += string[i]
    return output

class HTTPRequests(httpt.HTTPTest):
    """
    This test is also known as Header Field manipulation. It performes HTTP
    requests with variations in capitalization towards the backend.
    """
    name = "HTTPRequests"
    author = "Arturo Filastò"
    version = 0.1

    optParameters = [['backend', 'b', None, 'URL of the backend to use for sending the requests']]

    requiredOptions = ['backend']

    def processInputs(self):
        if self.localOptions['backend']:
            self.url = self.localOptions['backend']
        else:
            raise Exception("No backend specified")

    def test_get(self):
        return self.doRequest(self.url, "GET")

    def test_get_random_capitalization(self):
        method = random_capitalization("GET")
        return self.doRequest(self.url, method)

    def test_post(self):
        return self.doRequest(self.url, "POST")

    def test_post_random_capitalization(self):
        method = random_capitalization("POST")
        return self.doRequest(self.url, method)

    def test_put(self):
        return self.doRequest(self.url, "PUT")

    def test_put_random_capitalization(self):
        method = random_capitalization("PUT")
        return self.doRequest(self.url, method)


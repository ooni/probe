# -*- encoding: utf-8 -*-
#
# The purpose of this collector is to compute the eigenvector for the input
# file containing a list of sites.
#
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.kit import domclass
from ooni.templates import httpt

class DOMClassCollector(httpt.HTTPTest):
    name = "DOM class collector"
    author = "Arturo Filastò"
    version = 0.1

    followRedirects = True

    inputFile = ['file', 'f', None, 'The list of urls to build a domclass for']
    requiresTor = False
    requiresRoot = False

    def test_collect(self):
        if self.input:
            url = self.input
            return self.doRequest(url)
        else:
            raise Exception("No input specified")

    def processResponseBody(self, body):
        eigenvalues = domclass.compute_eigenvalues_from_DOM(content=body)
        self.report['eigenvalues'] = eigenvalues.tolist()

# -*- encoding: utf-8 -*-
#
# The purpose of this collector is to compute the eigenvector for the input
# file containing a list of sites.
#
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import threads, defer

from ooni.kit import domclass
from ooni.templates import httpt
from ooni.utils.log import msg, warn

class DOMClassCollector(httpt.HTTPTest):
    name = "DOM class collector"
    author = "Arturo Filastò"
    version = 0.1

    followRedirects = True

    inputFile = ['file', 'f', None, 'The list of urls to build a domclass for']

    def test_collect(self):
        if self.input:
            url = self.input
            return self.doRequest(url)
        else:
            raise Exception("No input specified")

    def processResponseBody(self, body):
        eigenvalues = domclass.compute_eigenvalues_from_DOM(content=body, parser=dom_parser)
        self.report['eigenvalues'] = eigenvalues.tolist()

def get_parser():
    """
    Returns the name of a valid parser to use with BeautifulSoup.
    If lxml or html5lib are available, uses these parsers
    """

    try:
        import lxml
        msg("Using BeautifulSoup with the 'lxml' parser")
        return "lxml"
    except ImportError:
        try:
            import html5lib
            msg("Using BeautifulSoup with the 'html5lib' parser")
            return "html5lib"
        except ImportError:
            warn("Warning: using BeautifulSoup with Python's default parser ('html.parser'). May not parse all DOM trees.")
            return None
dom_parser=get_parser()

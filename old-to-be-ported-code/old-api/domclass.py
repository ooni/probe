#!/usr/bin/env python
#-*- encoding: utf-8 -*-
#
#    domclass
#    ********
#
#    :copyright: (c) 2012 by Arturo Filastò
#    :license: see LICENSE for more details.
#
#    how this works
#    --------------
#
#    This classifier uses the DOM structure of a website to determine how similar
#    the two sites are.
#    The procedure we use is the following:
#        * First we parse all the DOM tree of the web page and we build a list of
#          TAG parent child relationships (ex. <html><a><b></b></a><c></c></html> =>
#          (html, a), (a, b), (html, c)).
#
#        * We then use this information to build a matrix (M) where m[i][j] = P(of
#          transitioning from tag[i] to tag[j]). If tag[i] does not exists P() = 0.
#          Note: M is a square matrix that is number_of_tags wide.
#
#        * We then calculate the eigenvectors (v_i) and eigenvalues (e) of M.
#
#        * The corelation between page A and B is given via this formula:
#          correlation = dot_product(e_A, e_B), where e_A and e_B are
#          resepectively the eigenvalues for the probability matrix A and the
#          probability matrix B.
#

try:
    import numpy
except:
    print "Error numpy not installed!"

import yaml
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.utils import log
from ooni.protocols.http import HTTPTest

class domclassArgs(usage.Options):
    optParameters = [['output', 'o', None, 'Output to write'],
                     ['file', 'f', None, 'Corpus file'],
                     ['fileb', 'b', None, 'Corpus file'],
                     ['urls', 'u', None, 'URL List'],
                     ['resume', 'r', 0, 'Resume at this index']]

# All HTML4 tags
# XXX add link to W3C page where these came from
alltags = ['A', 'ABBR', 'ACRONYM', 'ADDRESS', 'APPLET', 'AREA', 'B', 'BASE',
           'BASEFONT', 'BD', 'BIG', 'BLOCKQUOTE', 'BODY', 'BR', 'BUTTON', 'CAPTION',
           'CENTER', 'CITE', 'CODE', 'COL', 'COLGROUP', 'DD', 'DEL', 'DFN', 'DIR', 'DIV',
           'DL', 'DT', 'E M', 'FIELDSET', 'FONT', 'FORM', 'FRAME', 'FRAMESET', 'H1', 'H2',
           'H3', 'H4', 'H5', 'H6', 'HEAD', 'HR', 'HTML', 'I', 'IFRAME ', 'IMG',
           'INPUT', 'INS', 'ISINDEX', 'KBD', 'LABEL', 'LEGEND', 'LI', 'LINK', 'MAP',
           'MENU', 'META', 'NOFRAMES', 'NOSCRIPT', 'OBJECT', 'OL', 'OPTGROUP', 'OPTION',
           'P', 'PARAM', 'PRE', 'Q', 'S', 'SAMP', 'SCRIPT', 'SELECT', 'SMALL', 'SPAN',
           'STRIKE', 'STRONG', 'STYLE', 'SUB', 'SUP', 'TABLE', 'TBODY', 'TD',
           'TEXTAREA', 'TFOOT', 'TH', 'THEAD', 'TITLE', 'TR', 'TT', 'U', 'UL', 'VAR']

# Reduced subset of only the most common tags
commontags = ['A', 'B', 'BLOCKQUOTE', 'BODY', 'BR', 'BUTTON', 'CAPTION',
           'CENTER', 'CITE', 'CODE', 'COL', 'DD', 'DIV',
           'DL', 'DT', 'EM', 'FIELDSET', 'FONT', 'FORM', 'FRAME', 'FRAMESET', 'H1', 'H2',
           'H3', 'H4', 'H5', 'H6', 'HEAD', 'HR', 'HTML', 'IFRAME ', 'IMG',
           'INPUT', 'INS', 'LABEL', 'LEGEND', 'LI', 'LINK', 'MAP',
           'MENU', 'META', 'NOFRAMES', 'NOSCRIPT', 'OBJECT', 'OL', 'OPTION',
           'P', 'PRE', 'SCRIPT', 'SELECT', 'SMALL', 'SPAN',
           'STRIKE', 'STRONG', 'STYLE', 'SUB', 'SUP', 'TABLE', 'TBODY', 'TD',
           'TEXTAREA', 'TFOOT', 'TH', 'THEAD', 'TITLE', 'TR', 'TT', 'U', 'UL']

# The tags we are intested in using for our analysis
thetags = ['A', 'DIV', 'FRAME', 'H1', 'H2',
           'H3', 'H4', 'IFRAME ', 'INPUT',
           'LABEL','LI', 'P', 'SCRIPT', 'SPAN',
           'STYLE', 'TR']

def compute_probability_matrix(dataset):
    """
    Compute the probability matrix based on the input dataset.

    :dataset: an array of pairs representing the parent child relationships.
    """
    import itertools
    ret = {}
    matrix = numpy.zeros((len(thetags) + 1, len(thetags) + 1))

    for data in dataset:
        x = data[0].upper()
        y = data[1].upper()
        try:
            x = thetags.index(x)
        except:
            x = len(thetags)

        try:
            y = thetags.index(y)
        except:
            y = len(thetags)

        matrix[x,y] += 1

    for x in xrange(len(thetags) + 1):
        possibilities = 0
        for y in matrix[x]:
            possibilities += y

        for i in xrange(len(matrix[x])):
            if possibilities != 0:
                matrix[x][i] = matrix[x][i]/possibilities

    return matrix

def compute_eigenvalues(matrix):
    """
    Returns the eigenvalues of the supplied square matrix.

    :matrix: must be a square matrix and diagonalizable.
    """
    return numpy.linalg.eigvals(matrix)

def readDOM(content=None, filename=None):
    """
    Parses the DOM of the HTML page and returns an array of parent, child
    pairs.

    :content: the content of the HTML page to be read.

    :filename: the filename to be read from for getting the content of the
               page.
    """
    from bs4 import BeautifulSoup

    if filename:
        f = open(filename)
        content = ''.join(f.readlines())
        f.close()

    dom = BeautifulSoup(content)
    couples = []
    for x in dom.findAll():
        couples.append((str(x.parent.name), str(x.name)))

    return couples

class domclassTest(HTTPTest):
    implements(IPlugin, ITest)

    shortName = "domclass"
    description = "domclass"
    requirements = None
    options = domclassArgs
    blocking = False

    follow_redirects = True
    #tool = True

    def runTool(self):
        site_a = readDOM(filename=self.local_options['file'])
        site_b = readDOM(filename=self.local_options['fileb'])
        a = {}
        a['matrix'] = compute_probability_matrix(site_a)
        a['eigen'] = compute_eigenvalues(a['matrix'])

        self.result['eigenvalues'] = a['eigen']
        b = {}
        b['matrix'] = compute_probability_matrix(site_b)
        b['eigen'] = compute_eigenvalues(b['matrix'])

        #print "A: %s" % a
        #print "B: %s" % b
        correlation = numpy.vdot(a['eigen'],b['eigen'])
        correlation /= numpy.linalg.norm(a['eigen'])*numpy.linalg.norm(b['eigen'])
        correlation = (correlation + 1)/2
        print "Corelation: %s" % correlation
        self.end()
        return a

    def processResponseBody(self, data):
        site_a = readDOM(data)
        #site_b = readDOM(self.local_options['fileb'])
        a = {}
        a['matrix'] = compute_probability_matrix(site_a)
        a['eigen'] = compute_eigenvalues(a['matrix'])


        if len(data) == 0:
            self.result['eigenvalues'] = None
            self.result['matrix'] = None
        else:
            self.result['eigenvalues'] = a['eigen']
            #self.result['matrix'] = a['matrix']
        #self.result['content'] = data[:200]
        #b = compute_matrix(site_b)
        print "A: %s" % a
        return a['eigen']

    def load_assets(self):
        if self.local_options:
            if self.local_options['file']:
                self.tool = True
                return {}
            elif self.local_options['urls']:
                return {'url': Asset(self.local_options['urls'])}
            else:
                self.end()
                return {}
        else:
            return {}

#domclass = domclassTest(None, None, None)

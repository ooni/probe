"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
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
                     ['asset', 'a', None, 'URL List'],
                     ['resume', 'r', 0, 'Resume at this index']]
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

commontags = ['A', 'B', 'BLOCKQUOTE', 'BODY', 'BR', 'BUTTON', 'CAPTION',
           'CENTER', 'CITE', 'CODE', 'COL', 'DD', 'DIV',
           'DL', 'DT', 'EM', 'FIELDSET', 'FONT', 'FORM', 'FRAME', 'FRAMESET', 'H1', 'H2',
           'H3', 'H4', 'H5', 'H6', 'HEAD', 'HR', 'HTML', 'IFRAME ', 'IMG',
           'INPUT', 'INS', 'LABEL', 'LEGEND', 'LI', 'LINK', 'MAP',
           'MENU', 'META', 'NOFRAMES', 'NOSCRIPT', 'OBJECT', 'OL', 'OPTION',
           'P', 'PRE', 'SCRIPT', 'SELECT', 'SMALL', 'SPAN',
           'STRIKE', 'STRONG', 'STYLE', 'SUB', 'SUP', 'TABLE', 'TBODY', 'TD',
           'TEXTAREA', 'TFOOT', 'TH', 'THEAD', 'TITLE', 'TR', 'TT', 'U', 'UL']

thetags = ['A',
           'DIV',
           'FRAME', 'H1', 'H2',
           'H3', 'H4', 'IFRAME ', 'INPUT', 'LABEL','LI', 'P', 'SCRIPT', 'SPAN',
           'STYLE',
           'TR']

def compute_matrix(dataset):
    import itertools
    import numpy
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
    ret['matrix'] = matrix
    ret['eigen'] = numpy.linalg.eigvals(matrix)
    return ret

def readDOM(fn):
    from bs4 import BeautifulSoup
    #f = open(fn)
    #content = ''.join(f.readlines())
    content = fn
    dom = BeautifulSoup(content)
    couples = []
    for x in dom.findAll():
        couples.append((str(x.parent.name), str(x.name)))
    #f.close()
    return couples

class domclassTest(HTTPTest):
    implements(IPlugin, ITest)

    shortName = "domclass"
    description = "domclass"
    requirements = None
    options = domclassArgs
    blocking = False

    def runTool(self):
        import yaml, numpy
        site_a = readDOM(self.local_options['file'])
        site_b = readDOM(self.local_options['fileb'])
        a = compute_matrix(site_a)
        self.result['eigenvalues'] = str(a['eigen'])
        self.result['matrix'] = str(a['matrix'])
        self.result['content'] = data[:200]
        b = compute_matrix(site_b)
        print "A: %s" % a
        print "B: %s" % b
        correlation = numpy.vdot(a['eigen'],b['eigen'])
        correlation /= numpy.linalg.norm(a['eigen'])*numpy.linalg.norm(b['eigen'])
        correlation = (correlation + 1)/2
        print "Corelation: %s" % correlation

    def processResponseBody(self, data):
        import yaml, numpy
        site_a = readDOM(data)
        #site_b = readDOM(self.local_options['fileb'])
        a = compute_matrix(site_a)

        if len(data) == 0:
            self.result['eigenvalues'] = None
            self.result['matrix'] = None
        else:
            self.result['eigenvalues'] = str(a['eigen'])
            self.result['matrix'] = str(a['matrix'])
        #self.result['content'] = data[:200]
        #b = compute_matrix(site_b)
        print "A: %s" % a
        return a
        #print "B: %s" % b
        #correlation = numpy.vdot(a['eigen'],b['eigen'])
        #correlation /= numpy.linalg.norm(a['eigen'])*numpy.linalg.norm(b['eigen'])
        #correlation = (correlation + 1)/2
        # print "Corelation: %s" % correlation

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
domclass = domclassTest(None, None, None)

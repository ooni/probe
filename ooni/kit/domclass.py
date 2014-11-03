"""
how this works
--------------

This classifier uses the DOM structure of a website to determine how similar
the two sites are.
The procedure we use is the following:
   * First we parse all the DOM tree of the web page and we build a list of
     TAG parent child relationships (ex. <html><a><b></b></a><c></c></html> =>
     (html, a), (a, b), (html, c)).

   * We then use this information to build a matrix (M) where m[i][j] = P(of
     transitioning from tag[i] to tag[j]). If tag[i] does not exists P() = 0.
     Note: M is a square matrix that is number_of_tags wide.

   * We then calculate the eigenvectors (v_i) and eigenvalues (e) of M.

   * The corelation between page A and B is given via this formula:
     correlation = dot_product(e_A, e_B), where e_A and e_B are
     resepectively the eigenvalues for the probability matrix A and the
     probability matrix B.
"""

import numpy
import time

from ooni import log

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

def readDOM(content=None, filename=None, debug=False):
    """
    Parses the DOM of the HTML page and returns an array of parent, child
    pairs.

    :content: the content of the HTML page to be read.

    :filename: the filename to be read from for getting the content of the
               page.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.err("BeautifulSoup is not installed. This test canno run")
        raise Exception

    if filename:
        f = open(filename)
        content = ''.join(f.readlines())
        f.close()

    if debug:
        start = time.time()
        print "Running BeautifulSoup on content"
    dom = BeautifulSoup(content)
    if debug:
        print "done in %s" % (time.time() - start)

    if debug:
        start = time.time()
        print "Creating couples matrix"
    couples = []
    for x in dom.findAll():
        couples.append((str(x.parent.name), str(x.name)))
    if debug:
        print "done in %s" % (time.time() - start)

    return couples

def compute_eigenvalues_from_DOM(*arg,**kw):
    dom = readDOM(*arg, **kw)
    probability_matrix = compute_probability_matrix(dom)
    eigenvalues = compute_eigenvalues(probability_matrix)
    return eigenvalues

def compute_correlation(matrix_a, matrix_b):
    correlation = numpy.vdot(matrix_a, matrix_b)
    correlation /= numpy.linalg.norm(matrix_a)*numpy.linalg.norm(matrix_b)
    correlation = (correlation + 1)/2
    return correlation

def benchmark():
    """
    Running some very basic benchmarks on this input data:

    Data files:
    683 filea.txt
    678 fileb.txt

    diff file* | wc -l
    283

    We get such results:

    Read file B
    Running BeautifulSoup on content
    done in 0.768223047256
    Creating couples matrix
    done in 0.023903131485
    --------
    total done in 0.796372890472
    Read file A
    Running BeautifulSoup on content
    done in 0.752885818481
    Creating couples matrix
    done in 0.0163578987122
    --------
    total done in 0.770951986313
    Computing prob matrix
    done in 0.0475239753723
    Computing eigenvalues
    done in 0.00161099433899
    Computing prob matrix B
    done in 0.0408289432526
    Computing eigen B
    done in 0.000268936157227
    Computing correlation
    done in 0.00016713142395
    Corelation: 0.999999079331

    What this means is that the bottleneck is not in the maths, but is rather
    in the computation of the DOM tree matrix.

    XXX We should focus on optimizing the parsing of the HTML (this depends on
    beautiful soup). Perhaps we can find and alternative to it that is
    sufficient for us.
    """
    start = time.time()
    print "Read file B"
    site_a = readDOM(filename='filea.txt', debug=True)
    print "--------"
    print "total done in %s" % (time.time() - start)

    start = time.time()
    print "Read file A"
    site_b = readDOM(filename='fileb.txt', debug=True)
    print "--------"
    print "total done in %s" % (time.time() - start)

    a = {}
    b = {}

    start = time.time()
    print "Computing prob matrix"
    a['matrix'] = compute_probability_matrix(site_a)
    print "done in %s" % (time.time() - start)
    start = time.time()

    print "Computing eigenvalues"
    a['eigen'] = compute_eigenvalues(a['matrix'])
    print "done in %s" % (time.time() - start)
    start = time.time()

    start = time.time()
    print "Computing prob matrix B"
    b['matrix'] = compute_probability_matrix(site_b)
    print "done in %s" % (time.time() - start)

    start = time.time()
    print "Computing eigen B"
    b['eigen'] = compute_eigenvalues(b['matrix'])
    print "done in %s" % (time.time() - start)

    start = time.time()
    print "Computing correlation"
    correlation = compute_correlation(a['eigen'], b['eigen'])
    print "done in %s" % (time.time() - start)

    print "Corelation: %s" % correlation

#benchmark()

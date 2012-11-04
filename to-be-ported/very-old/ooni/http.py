#!/usr/bin/env python
#
# HTTP support for ooni-probe
# by Jacob Appelbaum <jacob@appelbaum.net>
#    Arturo Filasto' <art@fuffa.org>
#

from socket import gethostbyname
import ooni.common
import ooni.helpers
import ooni.report
import urllib2
import httplib
from urlparse import urlparse
from pprint import pprint
import pycurl
import random
import string
import re
from pprint import pprint
try:
   from BeautifulSoup import BeautifulSoup
except:
   pass                        # Never mind, let's break later.

# By default, we'll be Torbutton's UA
default_ua = { 'User-Agent' :
               'Mozilla/5.0 (Windows NT 6.1; rv:5.0) Gecko/20100101 Firefox/5.0' }

# Use pycurl to connect over a proxy
PROXYTYPE_SOCKS5 = 5
default_proxy_type = PROXYTYPE_SOCKS5
default_proxy_host = "127.0.0.1"
default_proxy_port = "9050"

#class HTTPResponse(object):
#  def __init__(self):


"""A very basic HTTP fetcher that uses Tor by default and returns a curl
   object."""
def http_proxy_fetch(url, headers, proxy_type=5,
                     proxy_host="127.0.0.1",
                     proxy_port=9050):
   request = pycurl.Curl()
   request.setopt(pycurl.PROXY, proxy_host)
   request.setopt(pycurl.PROXYPORT, proxy_port)
   request.setopt(pycurl.PROXYTYPE, proxy_type)
   request.setopt(pycurl.HTTPHEADER, ["User-Agent: Mozilla/5.0 (Windows NT 6.1; rv:5.0) Gecko/20100101 Firefox/5.0"])
   request.setopt(pycurl.URL, url)
   response = request.perform()
   http_code = getinfo(pycurl.HTTP_CODE)
   return response, http_code

"""A very basic HTTP fetcher that returns a urllib2 response object."""
def http_fetch(url,
               headers= default_ua,
               label="generic HTTP fetch"):
   request = urllib2.Request(url, None, headers)
   response = urllib2.urlopen(request)
   return response

"""Connect to test_hostname on port 80, request url and compare it with the expected
   control_result. Optionally, a label may be set to customize
   output. If the experiment matches the control, this returns True with the http
   status code; otherwise it returns False.
"""
def http_content_match(experimental_url, control_result,
                       headers= { 'User-Agent' : default_ua },
                       label="generic HTTP content comparison"):
  request = urllib2.Request(experimental_url, None, headers)
  response = urllib2.urlopen(request)
  responseContents = response.read()
  responseCode = response.code
  if responseContents != False:
    if str(responseContents) != str(control_result):
      print label + " control " + str(control_result) + " data does not " \
            "match experiment response: " + str(responseContents)
      return False, responseCode
    return True, responseCode
  else:
    print "HTTP connection appears to have failed"
  return False, False

"""Connect to test_hostname on port 80, request url and compare it with the expected
   control_result as a regex. Optionally, a label may be set to customize
   output. If the experiment matches the control, this returns True with the HTTP
   status code; otherwise it returns False.
"""
def http_content_fuzzy_match(experimental_url, control_result,
                       headers= { 'User-Agent' : default_ua },
                       label="generic HTTP content comparison"):
  request = urllib2.Request(experimental_url, None, headers)
  response = urllib2.urlopen(request)
  responseContents = response.read()
  responseCode = response.code
  pattern = re.compile(control_result)
  match = pattern.search(responseContents)
  if responseContents != False:
    if not match:
      print label + " control " + str(control_result) + " data does not " \
            "match experiment response: " + str(responseContents)
      return False, responseCode
    return True, responseCode
  else:
    print "HTTP connection appears to have failed"
  return False, False

"""Compare two HTTP status codes as integers and return True if they match."""
def http_status_code_match(experiment_code, control_code):
  if int(experiment_code) != int(control_code):
    return False
  return True

"""Compare two HTTP status codes as integers and return True if they don't match."""
def http_status_code_no_match(experiment_code, control_code):
   if http_status_code_match(experiment_code, control_code):
     return False
   return True

"""Connect to a URL and compare the control_header/control_result with the data
served by the remote server. Return True if it matches, False if it does not."""
def http_header_match(experiment_url, control_header, control_result):
  response = http_fetch(url, label=label)
  remote_header = response.get_header(control_header)
  if str(remote_header) == str(control_result):
    return True
  else:
    return False

"""Connect to a URL and compare the control_header/control_result with the data
served by the remote server. Return True if it does not matche, False if it does."""
def http_header_no_match(experiment_url, control_header, control_result):
  match = http_header_match(experiment_url, control_header, control_result)
  if match:
    return False
  else:
    return True

def send_browser_headers(self, browser, conn):
  headers = ooni.helpers.get_random_headers(self)
  for h in headers:
    conn.putheader(h[0], h[1])
  conn.endheaders()
  return True

def http_request(self, method, url, path=None):
  purl = urlparse(url)
  host = purl.netloc
  conn = httplib.HTTPConnection(host, 80)
  conn.connect()
  if path is None:
    path = purl.path
  conn.putrequest(method, purl.path)
  send_browser_headers(self, None, conn)
  response = conn.getresponse()
  headers = dict(response.getheaders())
  self.headers = headers
  self.data = response.read()
  return True

def search_headers(self, s_headers, url):
  if http_request(self, "GET", url):
    headers = self.headers
  else:
    return None
  result = {}
  for h in s_headers.items():
    result[h[0]] = h[0] in headers
  return result

# XXX for testing
#  [('content-length', '9291'), ('via', '1.0 cache_server:3128 (squid/2.6.STABLE21)'), ('x-cache', 'MISS from cache_server'), ('accept-ranges', 'bytes'), ('server', 'Apache/2.2.16 (Debian)'), ('last-modified', 'Fri, 22 Jul 2011 03:00:31 GMT'), ('connection', 'close'), ('etag', '"105801a-244b-4a89fab1e51c0;49e684ba90c80"'), ('date', 'Sat, 23 Jul 2011 03:03:56 GMT'), ('content-type', 'text/html'), ('x-cache-lookup', 'MISS from cache_server:3128')]

"""Search for squid headers by requesting a random site and checking if the headers have been rewritten (active, not fingerprintable)"""
def search_squid_headers(self):
  test_name = "squid header"
  self.logger.info("RUNNING %s test" % test_name)
  url = ooni.helpers.get_random_url(self)
  s_headers = {'via': '1.0 cache_server:3128 (squid/2.6.STABLE21)', 'x-cache': 'MISS from cache_server', 'x-cache-lookup':'MISS from cache_server:3128'}
  ret = search_headers(self, s_headers, url)
  for i in ret.items():
    if i[1] is True:
      self.logger.info("the %s test returned False" % test_name)
      return False
  self.logger.info("the %s test returned True" % test_name)
  return True

def random_bad_request(self):
  url = ooni.helpers.get_random_url(self)
  r_str = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(random.randint(5,20)))
  if http_request(self, r_str, url):
    return True
  else:
    return None

"""Create a request made up of a random string of 5-20 chars (active technique, possibly fingerprintable)"""
def squid_search_bad_request(self):
  test_name = "squid bad request"
  self.logger.info("RUNNING %s test" % test_name)
  if random_bad_request(self):
    s_headers = {'X-Squid-Error' : 'ERR_INVALID_REQ 0'}
    for i in s_headers.items():
      if i[0] in self.headers:
        self.logger.info("the %s test returned False" % test_name)
        return False
    self.logger.info("the %s test returned True" % test_name)
    return True
  else:
    self.logger.warning("the %s test returned failed" % test_name)
    return None

"""Try requesting cache_object and expect as output access denied (very active technique, fingerprintable) """
def squid_cacheobject_request(self):
  url = ooni.helpers.get_random_url(self)
  test_name = "squid cacheobject"
  self.logger.info("RUNNING %s test" % test_name)
  if http_request(self, "GET", url, "cache_object://localhost/info"):
    soup = BeautifulSoup(self.data)
    if soup.find('strong') and soup.find('strong').string == "Access Denied.":
      self.logger.info("the %s test returned False" % test_name)
      return False
    else:
      self.logger.info("the %s test returned True" % test_name)
      return True
  else:
    self.logger.warning("the %s test failed" % test_name)
    return None


def MSHTTP_CP_Tests(self):
  test_name = "MS HTTP Captive Portal"
  self.logger.info("RUNNING %s test" % test_name)
  experiment_url = "http://www.msftncsi.com/ncsi.txt"
  expectedResponse = "Microsoft NCSI" # Only this - nothing more
  expectedResponseCode = "200" # Must be this - nothing else
  label = "MS HTTP"
  headers = { 'User-Agent' : 'Microsoft NCSI' }
  content_match, experiment_code = http_content_match(experiment_url, expectedResponse,
                         headers, label)
  status_match = http_status_code_match(expectedResponseCode,
                        experiment_code)
  if status_match and content_match:
    self.logger.info("the %s test returned True" % test_name)
    return True
  else:
    print label + " experiment would conclude that the network is filtered."
    self.logger.info("the %s test returned False" % test_name)
    return False

def AppleHTTP_CP_Tests(self):
  test_name = "Apple HTTP Captive Portal"
  self.logger.info("RUNNING %s test" % test_name)
  experiment_url = "http://www.apple.com/library/test/success.html"
  expectedResponse = "Success" # There is HTML that contains this string
  expectedResponseCode = "200"
  label = "Apple HTTP"
  headers = { 'User-Agent' : 'Mozilla/5.0 (iPhone; U; CPU like Mac OS X; en) '
                           'AppleWebKit/420+ (KHTML, like Gecko) Version/3.0'
                           ' Mobile/1A543a Safari/419.3' }
  content_match, experiment_code = http_content_fuzzy_match(
                                   experiment_url, expectedResponse, headers)
  status_match = http_status_code_match(expectedResponseCode,
                          experiment_code)
  if status_match and content_match:
    self.logger.info("the %s test returned True" % test_name)
    return True
  else:
    print label + " experiment would conclude that the network is filtered."
    print label + "content match:" + str(content_match) + " status match:" + str(status_match)
    self.logger.info("the %s test returned False" % test_name)
    return False

def WC3_CP_Tests(self):
  test_name = "W3 Captive Portal"
  self.logger.info("RUNNING %s test" % test_name)
  url = "http://tools.ietf.org/html/draft-nottingham-http-portal-02"
  draftResponseCode = "428"
  label = "WC3 draft-nottingham-http-portal"
  response = http_fetch(url, label=label)
  responseCode = response.code
  if http_status_code_no_match(responseCode, draftResponseCode):
    self.logger.info("the %s test returned True" % test_name)
    return True
  else:
    print label + " experiment would conclude that the network is filtered."
    print label + " status match:" + status_match
    self.logger.info("the %s test returned False" % test_name)
    return False

# Google ChromeOS fetches this url in guest mode
# and they expect the user to authenticate
def googleChromeOSHTTPTest(self):
  print "noop"
  #url = "http://www.google.com/"

def SquidHeader_TransparentHTTP_Tests(self):
  return search_squid_headers(self)

def SquidBadRequest_TransparentHTTP_Tests(self):
  return squid_search_bad_request(self)

def SquidCacheobject_TransparentHTTP_Tests(self):
  return squid_cacheobject_request(self)



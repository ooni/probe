# -*- encoding: utf-8 -*-

import socket
import socks
import select
from random import randint

from twisted.internet import defer 

from ooni.settings import config
from ooni.nettest import NetTestCase
from ooni.utils import log

message="""OPTIONS sip:%(dst_ip)s SIP/2.0
Via: SIP/2.0/%(proto)s %(src_ip)s:%(src_port)s;branch=z9hG4bK.6de2867f;rport;alias
From: sip:ooni@%(src_ip)s:%(src_port)s;tag=1b86697
To: sip:%(dst_ip)s
Call-ID: 28862103@%(src_ip)s:%(src_port)s
CSeq: 1 OPTIONS
Contact: sip:ooni@%(src_ip)s:%(src_port)s
Content-Length: 0
Max-Forwards: 70
User-Agent: OONIP
Accept: text/plain\r\n\r\n"""

class SIPRequestsTest(NetTestCase):

    name = "SIP Requests Test"
    author = "Samir Allous"
    version = "0.1"
    baseParameters = [["socksproxy", "s", None,
            "Specify a socks proxy to use for requests (ip:port)"],
                      ["timeout", "t", 2,
            "Specify timeout in seconds"]]
    inputFile = ["file", "f", None,
            "List of servers to perform SIP requests to (ip[:port][/proto]),\
             default port=5060"]
    requiredOptions = ["file"]
    tmp_vars = {
	"src_ip": "127.0.0.1",
	"src_port": 5060,
	"dst_ip": "127.0.0.1",
	"dst_port": 5060,
	"proto": "all"
    }
    reports = {
	"request": None,
	"response": None,
	"request_tor": None,
	"response_tor": None
    }

    def setUp(self):
	self.timeout = float(self.localOptions['timeout'])
	if("/" in self.input):
	  input2 = self.input.split("/")[0]
	  self.tmp_vars["proto"] = self.input.split("/")[1]
	  self.tmp_vars["proto"] = self.tmp_vars["proto"].upper()
	  if(":" in input2):
	    self.tmp_vars["dst_ip"] = input2.split(":")[0]
	    self.tmp_vars["dst_port"] = input2.split(":")[1]
	  else:
	    self.tmp_vars["dst_ip"] = input2
	    self.tmp_vars["dst_port"] = 5060
	else:
	  self.tmp_vars["proto"] = "all"
	  if(":" in self.input):
	    self.tmp_vars["dst_ip"] = self.input.split(":")[0]
	    self.tmp_vars["dst_port"] = self.input.split(":")[1]
	  else:
	    self.tmp_vars["dst_ip"] = self.input
	    self.tmp_vars["dst_port"] = 5060

    def doTcpRequest(self, msg, tor = False):
	if(not tor):
	  sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
	  sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
	  if self.localOptions['socksproxy']:
	    try:
		sockshost, socksport = self.localOptions['socksproxy'].split(':')
	    except ValueError:
		raise InvalidSocksProxyOption
	    socksport = int(socksport)
	    sock.setproxy(socks.PROXY_TYPE_SOCKS5, sockshost, socksport)
	  self.tmp_vars["src_port"] = randint(35000,65000)
	  sock.bind(('',self.tmp_vars["src_port"]))
	  self.d = sock.connect((self.tmp_vars["dst_ip"], int(self.tmp_vars["dst_port"])))
	  self.tmp_vars["proto"] = "TCP"
	  sock.send(msg % self.tmp_vars)
	  recv = sock.recvfrom(0xffff)
	  sock.close
	  self.reports["request"] = msg % self.tmp_vars
	  log.msg("Received Response: %s" % str(recv))
	  self.reports["response"] = recv
	else:
	  sock = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
	  sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
	  sock.setproxy(socks.PROXY_TYPE_SOCKS5, 'localhost', config.tor.socks_port)
	  self.tmp_vars["src_port"] = randint(35000,65000)
	  sock.bind(('',self.tmp_vars["src_port"]))
	  self.d = sock.connect((self.tmp_vars["dst_ip"], int(self.tmp_vars["dst_port"])))
	  self.tmp_vars["proto"] = "TCP"
	  sock.send(msg % self.tmp_vars)
	  recv = sock.recv(0xffff)
	  sock.close
	  self.reports["request_tor"] = msg % self.tmp_vars
	  log.msg("Received Response: %s" % str(recv))
	  self.reports["response_tor"] = recv

    def doUdpRequest(self, msg, tor = False):
	if(not tor):
	  sock = socks.socksocket(socket.AF_INET, socket.SOCK_DGRAM)
	  sock.setblocking(0)
	  sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
	  if self.localOptions['socksproxy']:
	    try:
		sockshost, socksport = self.localOptions['socksproxy'].split(':')
	    except ValueError:
		raise InvalidSocksProxyOption
	    socksport = int(socksport)
	    sock.setproxy(socks.PROXY_TYPE_SOCKS5, sockshost, socksport)
	  self.tmp_vars["src_port"] = randint(35000,65000)
	  sock.bind(('',self.tmp_vars["src_port"]))
	  sock.settimeout(self.timeout)
	  self.tmp_vars["proto"] = "UDP"
	  sock.sendto(msg % self.tmp_vars, (self.tmp_vars["dst_ip"], int(self.tmp_vars["dst_port"])))
	  read = [sock]
	  inputready,outputready,exceptready = select.select(read,[],[],self.timeout)
	  recv = ""
	  for s in inputready:
	      if s == sock:
		recv = sock.recvfrom(0xffff)
	  sock.close
	  self.reports["request"] = msg % self.tmp_vars
	  log.msg("Received Response: %s" % str(recv))
	  self.reports["response"] = recv
	else:
	  sock = socks.socksocket(socket.AF_INET, socket.SOCK_DGRAM)
	  sock.setblocking(0)
	  sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
	  sock.setproxy(socks.PROXY_TYPE_SOCKS5, 'localhost', config.tor.socks_port)
	  self.tmp_vars["src_port"] = randint(35000,65000)
	  sock.bind(('',self.tmp_vars["src_port"]))
	  sock.settimeout(self.timeout)
	  self.tmp_vars["proto"] = "UDP"
	  sock.sendto(msg % self.tmp_vars, (self.tmp_vars["dst_ip"], int(self.tmp_vars["dst_port"])))
	  read = [sock]
	  inputready,outputready,exceptready = select.select(read,[],[],self.timeout)
	  recv = ""
	  for s in inputready:
	      if s == sock:
		recv = sock.recvfrom(0xffff)
	  sock.close
	  self.reports["request_tor"] = msg % self.tmp_vars
	  log.msg("Received Response: %s" % str(recv))
	  self.reports["response_tor"] = recv

    def isUp(self, address, port):
	s = socket.socket()
	s.settimeout(self.timeout)
	try:
	  s.connect((address, int(port)))
	  s.close
	  return True
	  s.close
	except socket.error, e:
	  return False

    def addToReport(self, proto, request = None, response = None, request_tor = None,response_tor = None ,):
	log.debug("Adding data to report:")
	if(proto == "TCP"):
	  self.report["TCP_Request"]= request
	  if(response == ""):
	    self.report["UDP_Response"] = "There is a problem, maybe no response OR icmp (type 3, code 3)"
	  else:
	    self.report["TCP_Response"] = response
	  if request_tor:
	    self.report["TCP_Request_TOR"] = request_tor
	  if response_tor:
	    self.report["TCP_Response_TOR"] = response_tor
	elif(proto == "UDP"):
	  self.report["UDP_Request"]= request
	  if(response == ""):
	    self.report["UDP_Response"] = "There is a problem, maybe no response OR icmp (type 3, code 3)"
	  else:
	    self.report["UDP_Response"] = response
	  if request_tor:
	    self.report["UDP_Request_TOR"] = request_tor
	  if response_tor:
	    self.report["UDP_Response_TOR"] = response_tor

    def test_request(self):
	self.d = defer.succeed
	tcp = udp = False
	if(self.tmp_vars["proto"] == "all"):
	  tcp = udp = True
	elif(self.tmp_vars["proto"] == "TCP"):
	  tcp = True
	elif(self.tmp_vars["proto"] == "UDP"):
	  udp = True
	if(tcp):
	  if(self.isUp(self.tmp_vars["dst_ip"], self.tmp_vars["dst_port"])):
	    self.report["method"] = "OPTIONS"
	    log.msg("Performing OPTIONS request to %s" % self.input)
	    self.doTcpRequest(message)
	    if(config.tor_state and config.tor.socks_port):
		log.msg("Performing OPTIONS request to %s via Tor" % self.input)
		self.doTcpRequest(message, True)
	  else:
	    self.report["status"] = "connection_timeout"
	    log.msg("Connection timeout.")
	  self.addToReport("TCP", self.reports["request"], self.reports["response"],
				self.reports["request_tor"], self.reports["response_tor"])
	if(udp):
	  self.report["method"] = "OPTIONS"
	  log.msg("Performing OPTIONS request to %s" % self.input)
	  self.doUdpRequest(message)
	  if(config.tor_state and config.tor.socks_port):
		log.msg("Performing OPTIONS request to %s via Tor" % self.input)
		self.doUdpRequest(message, True)
	  self.addToReport("UDP", self.reports["request"], self.reports["response"],
				self.reports["request_tor"], self.reports["response_tor"])
	return self.d

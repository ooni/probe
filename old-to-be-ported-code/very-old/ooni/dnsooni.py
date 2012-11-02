#!/usr/bin/env python
#
# DNS support for ooni-probe
# by Jacob Appelbaum <jacob@appelbaum.net>
#

from socket import gethostbyname
import ooni.common

# requires python-dns
# (pydns.sourceforge.net)
try:
  import DNS
# Mac OS X needs this
except:
  try:
    import dns as DNS
  except:
    pass                        # Never mind, let's break later.
import random
from pprint import pprint

""" Wrap gethostbyname """
def dns_resolve(hostname):
  try:
    resolved_host = gethostbyname(hostname)
    return resolved_host
  except:
    return False

"""Perform a resolution on test_hostname and compare it with the expected
   control_resolved ip address. Optionally, a label may be set to customize
   output. If the experiment matches the control, this returns True; otherwise
   it returns False.
"""
def dns_resolve_match(experiment_hostname, control_resolved,
                       label="generic DNS comparison"):
  experiment_resolved = dns_resolve(experiment_hostname)
  if experiment_resolved == False:
    return None
  if experiment_resolved:
    if str(experiment_resolved) != str(control_resolved):
      print label + " control " + str(control_resolved) + " data does not " \
            "match experiment response: " + str(experiment_resolved)
      return False
    return True

def generic_DNS_resolve(experiment_hostname, experiment_resolver):
  if experiment_resolver == None:
    req = DNS.Request(name=experiment_hostname) # local resolver
  else:
    req = DNS.Request(name=experiment_hostname, server=experiment_resolver) #overide
  resolved_data = req.req().answers
  return resolved_data

""" Return a list of all known censors. """
def load_list_of_known_censors(known_proxy_file=None):
  proxyfile = "proxy-lists/ips.txt"
  known_proxy_file = open(proxyfile, 'r', 1)
  known_proxy_list = []
  for known_proxy in known_proxy_file.readlines():
    known_proxy_list.append(known_proxy)
  known_proxy_file.close()
  known_proxy_count = len(known_proxy_list)
  print "Loading " + str(known_proxy_count) + " known proxies..."
  return known_proxy_list, known_proxy_count

def load_list_of_test_hosts(hostfile=None):
  if hostfile == None:
    hostfile="censorship-lists/norwegian-dns-blacklist.txt"
  host_list_file = open(hostfile, 'r', 1)
  host_list = []
  for host_name in host_list_file.readlines():
    if host_name.isspace():
      continue
    else:
     host_list.append(host_name)
  host_list_file.close()
  host_count = len(host_list)
  #print "Loading " + str(host_count) + " test host names..."
  return host_list, host_count

""" Return True with a list of censors if we find a known censor from
    known_proxy_list in the experiment_data DNS response. Otherwise return
    False and None. """
def contains_known_censors(known_proxy_list, experiment_data):
  match = False
  proxy_list = []
  for answer in range(len(experiment_data)):
    for known_proxy in known_proxy_list:
      if answer == known_proxy:
        print "CONFLICT: known proxy discovered: " + str(known_proxy),
        proxy_list.append(known_proxy)
        match = True
  return match, proxy_list

""" Return True and the experiment response that failed to match."""
def compare_control_with_experiment(known_proxy_list, control_data, experiment_data):
  known_proxy_found, known_proxies = contains_known_censors(known_proxy_list, experiment_data)
  conflict_list = []
  conflict = False
  if known_proxy_found:
    print "known proxy discovered: " + str(known_proxies)
  for answer in range(len(control_data)):
    if control_data[answer]['data'] == experiment_data:
      print "control_data[answer]['data'] = " + str(control_data[answer]['data']) + "and experiment_data = " + str(experiment_data)
      continue
    else:
      conflict = True
      conflict_list.append(experiment_data)
      #print "CONFLICT: control_data: " + str(control_data) + " experiment_data: " + str(experiment_data),
  return conflict, conflict_list

def dns_DNS_BULK_Tests(self, hostfile=None,
                       known_good_resolver="8.8.8.8", test_resolver=None):
  tampering = False # By default we'll pretend the internet is nice
  tampering_list = []
  host_list, host_count = load_list_of_test_hosts()
  known_proxies, proxy_count = load_list_of_known_censors()
  check_count = 1
  if test_resolver == None:
    DNS.ParseResolvConf() # Set the local resolver as our default
  if self.randomize:
    random.shuffle(host_list) # This makes our list non-sequential for now
  for host_name in host_list:
    host_name = host_name.strip()
    print "Total progress: " + str(check_count) + " of " + str(host_count) + " hosts to check"
    print "Resolving with control resolver..."
    print "Testing " + host_name + " with control resolver: " + str(known_good_resolver)
    print "Testing " + host_name + " with experiment resolver: " + str(test_resolver)
    # XXX TODO - we need to keep track of the status of these requests and then resume them
    while True:
      try:
        control_data = generic_DNS_resolve(host_name, known_good_resolver)
        break
      except KeyboardInterrupt:
        print "bailing out..."
        exit()
      except DNS.Base.DNSError:
        print "control resolver appears to be failing..."
        continue
      except:
        print "Timeout; looping!"
        continue

    print "Resolving with experiment resolver..."
    while True:
      try:
        experiment_data = generic_DNS_resolve(host_name, test_resolver)
        break
      except KeyboardInterrupt:
        print "bailing out..."
        exit()
      except DNS.Base.DNSError:
        print "experiment resolver appears to be failing..."
        continue
      except:
        print "Timeout; looping!"
        continue

    print "Comparing control and experiment...",
    tampering, conflicts = compare_control_with_experiment(known_proxies, control_data, experiment_data)
    if tampering:
      tampering_list.append(conflicts)
      print "Conflicts with " + str(host_name) + " : " + str(conflicts)
    check_count = check_count + 1
  host_list.close()
  return tampering

""" Attempt to resolve random_hostname and return True and None if empty. If an
    address is returned we return False and the returned address.
"""
def dns_response_empty(random_hostname):
  response = dns_resolve(random_hostname)
  if response == False:
    return True, None
  return False, response

def dns_multi_response_empty(count, size):
  for i in range(count):
    randName = ooni.common._randstring(size)
    response_empty, response_ip = dns_response_empty(randName)
    if response_empty == True and response_ip == None:
      responses_are_empty = True
    else:
      print label + " " + randName + " found with value " + str(response_ip)
      responses_are_empty = False
  return responses_are_empty

""" Attempt to resolve one random host name per tld in tld_list where the
    hostnames are random strings with a length between min_length and
    max_length. Return True if list is empty, otherwise return False."""
def dns_list_empty(tld_list, min_length, max_length,
                   label="generic DNS list test"):
  for tld in tld_list:
    randName = ooni.common._randstring(min_length, max_length) + tld
    response_empty, response_ip = dns_response_empty(randName)
  return response_empty

# Known bad test
# Test for their DNS breakage and their HTTP MITM
# "Family Shield" is 208.67.222.123 and 208.67.220.123
# returns 67.215.65.130 for filtered sites like kink.com
# block.opendns.com is a block page where users are redirected
# 208.67.216.135 208.67.217.135 are the block pages currently point
# 67.215.65.132 is returned for NXDOMAINs and a visit with HTTP to that IP
# results in redirection to http://guide.opendns.com/main?url=sdagsad.com or
# whatever the HOST header says
# Amusingly - their Server header is: "OpenDNS Guide"
""" Return True if we are not being directed as known OpenDNS block pages."""
def OpenDNS_DNS_Tests(self):
  return OpenDNS_Censorship_DNS_TESTS(self)
  return OpenDNS_NXDomain_DNS_TESTS(self)

def OpenDNS_Censorship_DNS_TESTS(self):
  known_filter = "67.215.65.130"
  randName = ooni.common._randstring(10)
  redirected = dns_resolve_match(randName, known_filter, label="OpenDNS DNS Censorship comparison")
  if redirected:
    return False
  else:
    return True

def OpenDNS_NXDomain_DNS_TESTS(self):
  known_filter = "67.215.65.132"
  randName = ooni.common._randstring(10)
  redirected = dns_resolve_match(randName, known_filter, label="OpenDNS DNS NXDomain comparison")
  if redirected:
    return False
  else:
    return True

"""Returns True if the experiment_url returns the well known Italian block page."""
def cc_DNS_Tests_it(self):
  tampering = False # By default we'll pretend the internet is nice
  tampering_list = []
  conflicts = []
  known_good_resolver = "8.8.8.8"
  host_list, host_count = load_list_of_test_hosts("censorship-lists/italy-gamble-blocklist-07-22-11.txt")
  known_http_block_pages, known_block_count = load_list_of_test_hosts("proxy-lists/italy-http-ips.txt")
  known_censoring_resolvers, censoring_resolver_count = load_list_of_test_hosts("proxy-lists/italy-dns-ips.txt")

  check_count = 1
  DNS.ParseResolvConf()
  # Set the local resolver as our default
  if self.randomize:
    random.shuffle(host_list) # This makes our list non-sequential for now
  print "We're testing (" + str(host_count) + ") URLs"
  print "We're looking for (" + str(known_block_count) + ") block pages"
  print "We're testing against (" + str(censoring_resolver_count) + ") censoring DNS resolvers"
  for test_resolver in known_censoring_resolvers:
    test_resolver = test_resolver.strip()
    for host_name in host_list:
      host_name = host_name.strip()
      print "Total progress: " + str(check_count) + " of " + str(host_count) + " hosts to check"
      print "Testing " + host_name + " with control resolver: " + known_good_resolver
      print "Testing " + host_name + " with experiment resolver: " + test_resolver
      while True:
        try:
          control_data = generic_DNS_resolve(host_name, known_good_resolver)
          break
        except KeyboardInterrupt:
          print "bailing out..."
          exit()
        except DNS.Base.DNSError:
          print "control resolver appears to be failing..."
          break
        except:
          print "Timeout; looping!"
          continue

      while True:
        try:
          experiment_data = generic_DNS_resolve(host_name, test_resolver)
          break
        except KeyboardInterrupt:
          print "bailing out..."
          exit()
        except DNS.Base.DNSError:
          print "experiment resolver appears to be failing..."
          continue
        except:
          print "Timeout; looping!"
          continue

      print "Comparing control and experiment...",
      tampering, conflicts = compare_control_with_experiment(known_http_block_pages, control_data, experiment_data)
      if tampering:
        tampering_list.append(conflicts)
        print "Conflicts with " + str(host_name) + " : " + str(conflicts)
      check_count = check_count + 1

  host_list.close()
  return tampering


## XXX TODO
## Code up automatic tests for HTTP page checking in Italy - length + known strings, etc

""" Returns True if the experiment_host returns a well known Australian filter
    IP address."""
def Australian_DNS_Censorship(self, known_filtered_host="badhost.com"):
  # http://www.robtex.com/ip/61.88.88.88.html
  # http://requests.optus.net.au/dns/
  known_block_ip = "208.69.183.228" # http://interpol.contentkeeper.com/
  known_censoring_resolvers = ["61.88.88.88"] # Optus
  for resolver in known_censoring_resolvers:
    blocked = generic_DNS_censorship(known_filtered_host, resolver, known_block_page)
    if blocked:
      return True

"""Returns True if experiment_hostname as resolved by experiment_resolver
   resolves to control_data. Returns False if there is no match or None if the
   attempt fails."""
def generic_DNS_censorship(self, experiment_hostname, experiment_resolver,
                           control_data):
  req = DNS.Request(name=experiment_hostname, server=experiment_resolver)
  resolved_data = s.req().answers
  for answer in range(len(resolved_data)):
    if resolved_data[answer]['data'] == control_data:
      return True
  return False

# See dns_launch_wildcard_checks in tor/src/or/dns.c for Tor implementation
# details
""" Return True if Tor would consider the network fine; False if it's hostile
    and has no signs of DNS tampering. """
def Tor_DNS_Tests(self):
  response_rfc2606_empty = RFC2606_DNS_Tests(self)
  tor_tld_list = ["", ".com", ".org", ".net"]
  response_tor_empty = ooni.dnsooni.dns_list_empty(tor_tld_list, 8, 16, "TorDNSTest")
  return response_tor_empty | response_rfc2606_empty

""" Return True if RFC2606 would consider the network hostile; False if it's all
    clear and has no signs of DNS tampering. """
def RFC2606_DNS_Tests(self):
  tld_list = [".invalid", ".test"]
  return ooni.dnsooni.dns_list_empty(tld_list, 4, 18, "RFC2606Test")

""" Return True if googleChromeDNSTest would consider the network OK."""
def googleChrome_CP_Tests(self):
    maxGoogleDNSTests = 3
    GoogleDNSTestSize = 10
    return ooni.dnsooni.dns_multi_response_empty(maxGoogleDNSTests,
                                            GoogleDNSTestSize)
def googleChrome_DNS_Tests(self):
    return googleChrome_CP_Tests(self)

""" Return True if MSDNSTest would consider the network OK."""
def MSDNS_CP_Tests(self):
    experimentHostname = "dns.msftncsi.com"
    expectedResponse = "131.107.255.255"
    return ooni.dnsooni.dns_resolve_match(experimentHostname, expectedResponse, "MS DNS")

def MSDNS_DNS_Tests(self):
    return MSDNS_CP_Tests(self)

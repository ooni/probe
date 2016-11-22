Details
=======

*Test Name*: Web Connectivity

*Current version*: 0.1.0

*NetTest*: Web Connectivity Test (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/nettests/blocking/web_connectivity.py)

*Test Helper*: Web Connectivity and DNS Discovery Helpers (https://github.com/TheTorProject/ooni-backend/blob/master/oonib/testhelpers/http_helpers.py)

*Test Type*: Content Blocking

*Requires Root*: No

Description
===========

This is a combined web connectivity test providing information on end-to-end
connectivity to a remote server. The test provides information revealing
discrepancies at the DNS, TCP, and HTTP levels.

The results of these local probes are compared with the results by a control
test, either performed directly through tor, or to a server accessed over a
standard HTTPS connection.

How to run the test
===================

`ooniprobe blocking/web_connectivity [-u <url>|-f <input file>] [-d <DNS discovery server>] [-r <retries>] [-b <backend>]`

*url* is a single URL to test.

*input file* is a file containing 1 URL per line which will be tested.

*DNS discovery server* is a DNS server to use to lookup names.

*retries* is the number of retries for the HTTP request, defaults to 1.

*backend* is the address of the control server to compare against.

Sample report
=============

From running:
`ooniprobe blocking/web_connectivity -f test_inputs/http_host_file.txt`

::

###########################################
# OONI Probe Report for web_connectivity (0.1.0)
# Tue Jul 12 10:27:09 2016
###########################################
---
annotations: null
data_format_version: 0.2.0
input_hashes: [a5da71ab5f265d396da13e2e9c2ca3ed43db010e9702d46ca7329c9d4ab33e81]
options: [-f, text.txt]
probe_asn: AS7922
probe_cc: US
probe_city: null
probe_ip: 127.0.0.1
report_id: 20160712T172644Z_AS7922_obPihyuYvZu6JmCKxb7NLCJgjJu7B1Zqbs6QuFxeJK1iPxJH0y
software_name: ooniprobe
software_version: 1.5.1
test_helpers:
backend: {address: 'httpo://7jne2rpg5lsaqs6b.onion', type: onion}
test_name: web_connectivity
test_start_time: '2016-07-12 17:27:08'
test_version: 0.1.0
...
---
accessible: true
agent: redirect
blocking: false
body_length_match: true
body_proportion: 0.9927186072681539
client_resolver: 74.125.80.4
control:
dns:
addrs: [216.58.198.36]
failure: null
http_request:
body_length: 44991
failure: null
headers: {Accept-Ranges: none, Alt-Svc: 'quic=":443"; ma=2592000; v="36,35,34,33,32,31,30,29,28,27,26,25"',
  Alternate-Protocol: '443:quic', Cache-Control: 'private, max-age=0', Content-Type: text/html;
    charset=ISO-8859-7, Date: 'Tue, 12 Jul 2016 17:27:12 GMT', Expires: '-1',
  P3P: 'CP="This is not a P3P policy! See https://www.google.com/support/accounts/answer/151657?hl=en
    for more info."', Server: gws,
  Vary: Accept-Encoding, X-Frame-Options: SAMEORIGIN, X-XSS-Protection: 1; mode=block,
  content-encoding: ''}
status_code: 200
title: Google
tcp_connect:
216.58.193.100:443: {failure: null, status: true}
control_failure: null
dns_consistency: consistent
dns_experiment_failure: null
headers_match: true
http_experiment_failure: null
input: https://www.google.com
measurement_start_time: '2016-07-12 17:27:09'
queries:
- answers:
- {answer_type: A, ipv4: 216.58.193.100}
failure: null
hostname: www.google.com
query_type: A
resolver_hostname: null
resolver_port: null
requests:
- failure: null
request:
body: null
headers: {Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  Accept-Language: 'en-US;q=0.8,en;q=0.5', User-Agent: 'Mozilla/5.0 (Windows NT
    6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'}
method: GET
tor: {exit_ip: null, exit_name: null, is_tor: false}
url: https://www.google.com
response:
body: {data: SNIP,
  format: base64}
code: 200
headers: {Accept-Ranges: none, Alt-Svc: 'quic=":443"; ma=2592000; v="36,35,34,33,32,31,30,29,28,27,26,25"',
  Alternate-Protocol: '443:quic', Cache-Control: 'private, max-age=0', Content-Type: text/html;
    charset=ISO-8859-1, Date: 'Tue, 12 Jul 2016 17:27:10 GMT', Expires: '-1',
  P3P: 'CP="This is not a P3P policy! See https://www.google.com/support/accounts/answer/151657?hl=en
    for more info."', Server: gws,
  Vary: Accept-Encoding, X-Frame-Options: SAMEORIGIN, X-XSS-Protection: 1; mode=block,
  content-encoding: ''}
retries: 1
socksproxy: null
status_code_match: true
tcp_connect:
- ip: 216.58.193.100
port: 443
status: {blocked: false, failure: null, success: true}
test_runtime: 3.8490829467773438
title_match: true
...

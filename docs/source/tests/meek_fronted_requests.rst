Details
=======

*Test Name*: Meek Fronted Request Test

*Current version*: 0.0.1

*NetTest*: HTTP Requests (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/blocking/meek_fronted_requests.py)

*Test Helper*: None

*Test Type*: Content Blocking, Traffic Manipulation

*Requires Root*: No

Description
===========

Performs a HTTP GET request to a list of fronted domains with the Host
Header of the "inside" meek-server. The meek-server handles a GET request and
response with: "I’m just a happy little web server.\n".

It tests if the fronted request/response to the meek server is successful.


How to run the test
===================

To test if the default meek servers are blocked:

`ooniprobe blocking/meek_fronted_requests`

To test a set of meek servers from a list containing hosts to test run:

`ooniprobe blocking/meek_fronted_requests -f <input_file>`

*input file* a list of domainName:hostHeader pairs to perform the test.

Optional test options
=====================

*-B* Expected body content from GET response (meek server default: 'I’m just a
happy little web server.\n')
*-D* Specify a single fronted domainName to test.
*-H* Specify "inside" Host Header to test.

Sample report
=============

`ooniprobe blocking/meek_fronted_requests`

::

###########################################
# OONI Probe Report for meek_fronted_requests_test (0.0.1)
# Thu Oct 15 22:01:32 2015
###########################################
---
input_hashes: []
options: []
probe_asn: AS20676
probe_cc: DE
probe_city: null
probe_ip: 127.0.0.1
report_id: null
software_name: ooniprobe
software_version: 1.3.1
start_time: 1444932091.0
test_helpers: {}
test_name: meek_fronted_requests_test
test_version: 0.0.1
...
---
agent: agent
input: [a0.awsstatic.com, d2zfqthxsdq309.cloudfront.net]
requests:
- request:
    body: null
    headers:
    - - Host
      - [d2zfqthxsdq309.cloudfront.net]
    method: GET
    tor: {is_tor: false}
    url: https://a0.awsstatic.com
  response:
    body: "I\u2019m just a happy little web server.\n"
    code: 200
    headers:
    - - Content-Length
      - ['38']
    - - Via
      - [1.1 15191055e43ba835d0fead01ae84015c.cloudfront.net (CloudFront)]
    - - X-Cache
      - [Hit from cloudfront]
    - - Age
      - ['530']
    - - Connection
      - [close]
    - - X-Amz-Cf-Id
      - [PKUBrpXDpoi2rSZ-WV0YUzX1wPg6JylZ_37iQeRQJB-xDLtJddcxzw==]
    - - Date
      - ['Thu, 15 Oct 2015 19:52:47 GMT']
    - - Content-Type
      - [text/plain; charset=utf-8]
socksproxy: null
success: true
test_runtime: 0.3198120594024658
test_start_time: 1444932097.0
...
---
agent: agent
input: [ajax.aspnetcdn.com, az668014.vo.msecnd.net]
requests:
- request:
    body: null
    headers:
    - - Host
      - [az668014.vo.msecnd.net]
    method: GET
    tor: {is_tor: false}
    url: https://ajax.aspnetcdn.com
  response:
    body: "I\u2019m just a happy little web server.\n"
    code: 200
    headers:
    - - Date
      - ['Thu, 15 Oct 2015 20:01:37 GMT']
    - - Content-Length
      - ['38']
    - - Content-Type
      - [text/plain; charset=utf-8]
    - - Connection
      - [close]
    - - Server
      - [ECAcc (fcn/40C4)]
socksproxy: null
success: true
test_runtime: 0.4580512046813965
test_start_time: 1444932097.0
...

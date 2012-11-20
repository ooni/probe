Details
=======

*Test Name*: DNS Tamper

*Current version*: 0.3

*NetTest*: DNSTamperTest (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/nettests/core/dnstamper.py)

*Test Helper*: DNSTestHelper (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/oonib/testhelpers/dns_helpers.py)

*Test Type*: Content Blocking

*Requires Root*: No

Description
===========

This test performs A queries to a set of test resolvers and a known good
control resolver. If the two results do not match it will perform a reverse DNS
lookup on the first A record address of both sets and check if they both
resolve to the same name.

NOTE: This test frequently results in false positives due to GeoIP-based
load balancing on major global sites such as google, facebook, and
youtube, etc.

How to run the test
===================

`./bin/ooniprobe nettests/core/dnstamper.py -t <test resolvers file> -f <input file> -b IP:PORT`

*test resolvers file* is a file containing the IP addresses of the resolvers to test for censorship, one per line.

*input file* is a file containing the hostnames to check for tampering.

*IP:PORT* is the address of the known good "control" resolver.

Sample report
=============

From running:
`./bin/ooniprobe nettests/core/dnstamper.py -t test_inputs/dns_tamper_test_resolvers.txt -f test_inputs/http_host_file.txt`

::

  ###########################################
  # OONI Probe Report for DNS tamper test
  # Tue Nov 20 20:38:54 2012
  ###########################################
  ---
  {probe_asn: null, probe_cc: null, probe_ip: 127.0.0.1, software_name: ooniprobe, software_version: 0.0.7.1-alpha,
    start_time: 1353436734.0, test_name: DNS tamper, test_version: '0.3'}
  ...
  ---
  input: torproject.org
  report:
    control_resolver: &id001 [8.8.8.8, 53]
    queries:
    - addrs: [86.59.30.40, 38.229.72.14, 38.229.72.16, 82.195.75.101]
      answers:
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=86.59.30.40
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=38.229.72.14
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=38.229.72.16
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=82.195.75.101
          ttl=142>]
      query: '[Query(''torproject.org'', 1, 1)]'
      query_type: A
      resolver: *id001
    - addrs: [86.59.30.40, 38.229.72.14, 38.229.72.16, 82.195.75.101]
      answers:
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=86.59.30.40
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=38.229.72.14
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=38.229.72.16
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=82.195.75.101
          ttl=142>]
      query: '[Query(''torproject.org'', 1, 1)]'
      query_type: A
      resolver: [8.8.8.8, 53]
    - addrs: [86.59.30.40, 38.229.72.14, 38.229.72.16, 82.195.75.101]
      answers:
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=86.59.30.40
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=38.229.72.14
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=38.229.72.16
          ttl=142>]
      - [<RR name=torproject.org type=A class=IN ttl=142s auth=False>, <A address=82.195.75.101
          ttl=142>]
      query: '[Query(''torproject.org'', 1, 1)]'
      query_type: A
      resolver: [8.8.4.4, 53]
    tampering: {8.8.4.4: false, 8.8.8.8: false}
    test_resolvers: [8.8.8.8, 8.8.4.4]
  test_name: test_a_queries
  test_started: 1353440334.075345
  ...
  ---
  input: ooni.nu
  report:
    control_resolver: &id001 [8.8.8.8, 53]
    queries:
    - addrs: [178.79.139.176]
      answers:
      - [<RR name=ooni.nu type=A class=IN ttl=1478s auth=False>, <A address=178.79.139.176
          ttl=1478>]
      query: '[Query(''ooni.nu'', 1, 1)]'
      query_type: A
      resolver: *id001
    - addrs: [178.79.139.176]
      answers:
      - [<RR name=ooni.nu type=A class=IN ttl=1478s auth=False>, <A address=178.79.139.176
          ttl=1478>]
      query: '[Query(''ooni.nu'', 1, 1)]'
      query_type: A
      resolver: [8.8.8.8, 53]
    - addrs: [178.79.139.176]
      answers:
      - [<RR name=ooni.nu type=A class=IN ttl=1478s auth=False>, <A address=178.79.139.176
          ttl=1478>]
      query: '[Query(''ooni.nu'', 1, 1)]'
      query_type: A
      resolver: [8.8.4.4, 53]
    tampering: {8.8.4.4: false, 8.8.8.8: false}
    test_resolvers: [8.8.8.8, 8.8.4.4]
  test_name: test_a_queries
  test_started: 1353440334.077116
  ...


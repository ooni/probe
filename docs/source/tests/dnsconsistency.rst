Details
=======

*Test Name*: DNS Consistency (Ex DNS Tamper)

*Current version*: 0.4

*NetTest*: DNS Consistency Test (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/nettests/blocking/dns_consistency.py)

*Test Helper*: DNS Test Helper (https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/dns_helpers.py)

*Test Type*: Content Blocking

*Requires Root*: No

Description
===========

This test performs A queries to a set of test resolvers and a known good
control resolver. If the two results do not match it will perform a reverse DNS
lookup on the first A record address of both sets and check if they both
resolve to the same name.

NOTE: This test frequently results in false positives due to GeoIP-based
load balancing on major global sites such as Google, Facebook, and
Youtube, etc.

How to run the test
===================

`ooniprobe blocking/dns_consistency [-t <test resolvers>|-T <test resolver file>-f <input file> -b IP:PORT`

*test resolvers* is a single test resolver (IP address)

*test resolvers file* is a file containing the IP addresses of the resolvers to test for censorship, one per line.

*input file* is a file containing hostnames or urls to check for tampering.

*IP:PORT* is the address of the known good "control" resolver.

Sample report
=============

From running:
`ooniprobe blocking/dns_consistency -T test_inputs/dns_tamper_test_resolvers.txt -f test_inputs/http_host_file.txt`

::

    ###########################################
    # OONI Probe Report for DNS tamper test
    # Thu Nov 29 12:17:19 2012
    ###########################################
    ---
    options:
      collector: null
      help: 0
      logfile: null
      pcapfile: null
      reportfile: null
      resume: 0
      subargs: [-t, 8.8.8.8, -f, test_inputs/dns_tamper_file.txt]
      test: nettests/blocking/dns_consistency.py
    probe_asn: null
    probe_cc: null
    probe_ip: 127.0.0.1
    software_name: ooniprobe
    software_version: 0.0.7.1-alpha
    start_time: 1354184239.0
    test_name: DNS tamper
    test_version: '0.4'
    ...
    ---
    input: torproject.org
    report:
      control_resolver: &id001 [8.8.8.8, 53]
      queries:
      - addrs: [86.59.30.40, 38.229.72.14, 38.229.72.16, 82.195.75.101]
        answers:
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=86.59.30.40
            ttl=91>]
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=38.229.72.14
            ttl=91>]
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=38.229.72.16
            ttl=91>]
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=82.195.75.101
            ttl=91>]
        query: '[Query(''torproject.org'', 1, 1)]'
        query_type: A
        resolver: *id001
      - addrs: [86.59.30.40, 38.229.72.14, 38.229.72.16, 82.195.75.101]
        answers:
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=86.59.30.40
            ttl=91>]
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=38.229.72.14
            ttl=91>]
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=38.229.72.16
            ttl=91>]
        - [<RR name=torproject.org type=A class=IN ttl=91s auth=False>, <A address=82.195.75.101
            ttl=91>]
        query: '[Query(''torproject.org'', 1, 1)]'
        query_type: A
        resolver: [8.8.8.8, 53]
      tampering: {8.8.8.8: false}
    test_name: test_a_lookup
    test_runtime: 0.0733950138092041
    test_started: 1354187839.508863
    ...
    ---
    input: google.com
    report:
      control_resolver: &id001 [8.8.8.8, 53]
      queries:
      - addrs: [173.194.69.100, 173.194.69.139, 173.194.69.113, 173.194.69.101, 173.194.69.138,
          173.194.69.102]
        answers:
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.100
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.139
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.113
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.101
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.138
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.102
            ttl=54>]
        query: '[Query(''google.com'', 1, 1)]'
        query_type: A
        resolver: *id001
      - addrs: [173.194.69.100, 173.194.69.139, 173.194.69.113, 173.194.69.101, 173.194.69.138,
          173.194.69.102]
        answers:
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.100
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.139
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.113
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.101
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.138
            ttl=54>]
        - [<RR name=google.com type=A class=IN ttl=54s auth=False>, <A address=173.194.69.102
            ttl=54>]
        query: '[Query(''google.com'', 1, 1)]'
        query_type: A
        resolver: [8.8.8.8, 53]
      tampering: {8.8.8.8: false}
    test_name: test_a_lookup
    test_runtime: 0.08325004577636719
    test_started: 1354187839.51091
    ...
    ---
    input: measurementlab.net
    report:
      control_resolver: &id001 [8.8.8.8, 53]
      queries:
      - addrs: [72.249.86.184]
        answers:
        - [<RR name=measurementlab.net type=A class=IN ttl=600s auth=False>, <A address=72.249.86.184
            ttl=600>]
        query: '[Query(''measurementlab.net'', 1, 1)]'
        query_type: A
        resolver: *id001
      - addrs: [72.249.86.184]
        answers:
        - [<RR name=measurementlab.net type=A class=IN ttl=600s auth=False>, <A address=72.249.86.184
            ttl=600>]
        query: '[Query(''measurementlab.net'', 1, 1)]'
        query_type: A
        resolver: [8.8.8.8, 53]
      tampering: {8.8.8.8: false}
    test_name: test_a_lookup
    test_runtime: 0.2565779685974121
    test_started: 1354187839.512434
    ...

Notes: Query is the string representation of :class:twisted.names.dns.Query


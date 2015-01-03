Details
=======

*Test Name*: DNS Spoof

*Current version*: 0.1

*NetTest*: DNSSpoof (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/manipulation/dns_spoof.py)

*Test Helper*: DNS Test Helper (https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/dns_helpers.py)

*Test Type*: Traffic Manipulation

*Requires Root*: Yes

Description
===========

This test performs A queries to a test resolver and a known good control resolver. The query is considered tampered with if the two responses match.

How to run the test
===================

`ooniprobe nettests/manipulation/dns_spoof.py [-s] [-k] [-i] -r <test resolver> -h <hostname> -b IP:PORT`

*test resolver* is a single test resolver (IP address).
*hostname* is the hostname to query.
*IP:PORT* is the address of the known good "control" resolver.
*-s, --ipsrc* Do *not* check if IP src and ICMP IP citation match
*-k, --seqack* Check if TCP sequence number and ACK match in the ICMP citation
*-i, --ipid* Check if the IPID matches when processing answers


Sample report
=============

From running:
`ooniprobe nettests/manipulation/dns_spoof.py -h torproject.org -r 4.2.2.2:53`

::

  ###########################################
  # OONI Probe Report for DNS Spoof test
  # Thu Dec  6 11:10:38 2012
  ###########################################
  ---
  options:
    collector: null
    help: 0
    logfile: null
    pcapfile: null
    reportfile: null
    resume: 0
    subargs: [-h, torproject.org, -r, '4.2.2.2:53']
    test: nettests/manipulation/dns_spoof.py
  probe_asn: null
  probe_cc: null
  probe_ip: 127.0.0.1
  software_name: ooniprobe
  software_version: 0.0.7.1-alpha
  start_time: 1354828238.0
  test_name: DNS Spoof
  test_version: 0.10000000000000001
  ...
  ---
  input: null
  report:
    answer_flags: [ipsrc]
    answered_packets:
    - - raw_packet: !!binary |
          RQAAfDj1AAA4EZJIBAICAn8AAAEANQA1AGjH/wAAgYAAAQAEAAAAAAp0b3Jwcm9qZWN0A29yZwAA
          AQABCnRvcnByb2plY3QDb3JnAAABAAEAAADnAAQm5UgQCnRvcnByb2plY3QDb3JnAAABAAEAAADn
          AARSw0tlCnRvcnByb2plY3QDb3JnAAABAAEAAADnAARWOx4oCnRvcnByb2plY3QDb3JnAAABAAEA
          AADnAAQm5UgO
        summary: 'IP / UDP / DNS Ans "38.229.72.16" '
    sent_packets:
    - - raw_packet: !!binary |
          RQAAPAABAABAEfWrfwAAAQQCAgIANQA1AChvjwAAAQAAAQAAAAAAAAp0b3Jwcm9qZWN0A29yZwAA
          AQAB
        summary: 'IP / UDP / DNS Qry "torproject.org" '
  test_name: test_a_lookup
  test_runtime: 0.23476505279541016
  test_started: 1354810238.400979
  ...
  ---
  input: null
  report:
    answer_flags: [ipsrc]
    answered_packets:
    - - raw_packet: !!binary |
          RQAAfGQmAAAvEWYLCAgICH8AAAEANQA1AGizfwAAgYAAAQAEAAAAAAp0b3Jwcm9qZWN0A29yZwAA
          AQABCnRvcnByb2plY3QDb3JnAAABAAEAAAOEAAQm5UgQCnRvcnByb2plY3QDb3JnAAABAAEAAAOE
          AARSw0tlCnRvcnByb2plY3QDb3JnAAABAAEAAAOEAARWOx4oCnRvcnByb2plY3QDb3JnAAABAAEA
          AAOEAAQm5UgO
        summary: 'IP / UDP / DNS Ans "38.229.72.16" '
    sent_packets:
    - - raw_packet: !!binary |
          RQAAPAABAABAEeuffwAAAQgICAgANQA1AChlgwAAAQAAAQAAAAAAAAp0b3Jwcm9qZWN0A29yZwAA
          AQAB
        summary: 'IP / UDP / DNS Qry "torproject.org" '
  test_name: test_control_a_lookup
  test_runtime: 0.23965692520141602
  test_started: 1354810238.625988
  ...
  ---
  input: null
  report: {spoofing: false}
  test_name: summary
  test_runtime: 0.00017499923706054688
  test_started: 1354810238.8703561
  ...

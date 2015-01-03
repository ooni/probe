Details
=======

*Test Name*: TCP Connect

*Current version*: 0.1

*NetTest*: TCP Connect Test (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/core/tcpconnect.py)

*Test Helper*: None

*Test Type*: Content Blocking

*Requires Root*: No

Description
===========

This test performs TCP connections to a set of specified IP:PORT pairs and
reports the reason for which it failed connecting to the target address.

The reason for failure may be: "timeout", when the connection timed out,
"refused", when the connection was dropped because of a RST or "failure" for a
reason that is not handled.

If the connection succeeds the test will report "success".

How to run the test
===================

`ooniprobe nettests/core/tcpconnect.py -f <input file>`

*input file* a list of IP:PORT pairs to perform TCP connections to.

Sample report
=============

From running:
`ooniprobe nettests/core/tcpconnect.py -f <input file>`

::

  ###########################################
  # OONI Probe Report for TCP Connect test
  # Tue Nov 20 17:00:50 2012
  ###########################################
  ---
  {probe_asn: null, probe_cc: null, probe_ip: 127.0.0.1, software_name: ooniprobe, software_version: 0.0.7.1-alpha,
    start_time: 1353423650.0, test_name: TCP Connect, test_version: '0.1'}
  ...
  ---
  input: 127.0.0.1:9050
  report: {connection: success}
  test_name: test_connect
  test_started: 1353427250.232331
  ...
  ---
  input: 127.0.0.1:8080
  report: {connection: failed}
  test_name: test_connect
  test_started: 1353427250.233206
  ...
  ---
  input: 127.0.0.1:1234
  report: {connection: failed}
  test_name: test_connect
  test_started: 1353427250.233974
  ...


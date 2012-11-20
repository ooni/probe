Details
=======

*Test Name*: Traceroute

*Current version*: 0.1.1

*NetTest*: Traceroute (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/nettests/core/traceroute.py)

*Test Helper*: Not yet implemented

*Test Type*: Traffic Manipulation

*Requires Root*: Yes

Description
===========

This test performs a multi port, multiprotocol traceroute test towards a
backend. The goal of such is to determine biases in the paths based on
destination port.

We perform a traceroute with destination port 22, 23, 80, 123, 443.

The test report includes the RAW IP packets sent and received. If the user has
disabled to include the source IP in the report then we will remove the source
IP for sent packets and the dst IP for sent packets.

The logged sent and received packets are only the ones that are generated and
received in userspace via the scapy super socket.

How to run the test
===================

`./bin/ooniprobe nettest/core/http_host.py -b <backend ip> -t <timeout> -m <max ttl>`

*backend ip* is the IP address of the backend to traceroute to

*timeout* timeout in seconds after which to give up waiting for an answer

*max ttl* maximum TTL to reach when doing a traceroute 

Sample report
=============

From running:
`./bin/ooniprobe nettests/core/traceroute.py -b 8.8.8.8`

::


  ###########################################
  # OONI Probe Report for Multi Protocol Traceroute Test test
  # Tue Nov 20 16:27:57 2012
  ###########################################
  ---
  {probe_asn: null, probe_cc: null, probe_ip: 127.0.0.1, software_name: ooniprobe, software_version: 0.0.7.1-alpha,
    start_time: 1353421677.0, test_name: Multi Protocol Traceroute Test, test_version: 0.1.1}
  ...
  ---
  input: null
  report:
    answered_packets:
    - - raw_packet: !!binary |
          RcAARHvUAABAAXiRwKgCAX8AAAELAMgUAAAAAEUAACiipAAAAQZEMsCoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 192.168.2.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    - - raw_packet: !!binary |
          RQAAOAhiAAA/Ae7PwKgBAX8AAAELAPMwAAAAAEUAACg8rwAAAQaqJ8CoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 192.168.1.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    - - raw_packet: !!binary |
          RcAAOCcmAAD9AVmvlxfiLX8AAAELAPMwAAAAAEUAACgfZQAAAQbHccCoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 151.23.226.45 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    - - raw_packet: !!binary |
          RcAAOEQ9AAD8AXncCgAzAX8AAAELAPMwAAAAAEUAAChevQAAAQaIGcCoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 10.0.51.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    - - raw_packet: !!binary |
          RcAAOKTfAAD7AarylwcVQX8AAAELAPMwAAAAAEUAACii4wAAAQZD88CoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 151.7.21.65 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    - - raw_packet: !!binary |
          RQAAOBw+AAD6AUJQlwcIRX8AAAELAPMvAAAAAUUAACgBdgAAAQblYMCoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 151.7.8.69 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD4AWQGlwYEzn8AAAELAPMwAAAAAEUAACjY8QAAAQYN5cCoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 151.6.4.206 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD3AWhGlwYBjn8AAAELAPMwAAAAAEUAACipZAAAAQY9csCoAkIICAgIABQBuwAAAAAA
          AAAAUAIgALsZAAA=
        summary: IP / ICMP 151.6.1.142 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    hops_123:
    - {address: 192.168.2.1, rtt: 0.008414983749389648, ttl: 1}
    - {address: 192.168.1.1, rtt: 0.020879030227661133, ttl: 2}
    - {address: 151.23.226.45, rtt: 0.037843942642211914, ttl: 3}
    - {address: 10.0.51.1, rtt: 0.04594087600708008, ttl: 4}
    - {address: 151.7.21.65, rtt: 0.06121087074279785, ttl: 5}
    - {address: 151.7.8.69, rtt: 0.07722091674804688, ttl: 6}
    - {address: 151.6.4.206, rtt: 0.10275506973266602, ttl: 7}
    - {address: 151.6.1.142, rtt: 0.11046791076660156, ttl: 8}
    hops_22:
    - {address: 192.168.2.1, rtt: 0.04184389114379883, ttl: 1}
    - {address: 192.168.1.1, rtt: 0.058888912200927734, ttl: 2}
    - {address: 151.23.226.45, rtt: 0.08370399475097656, ttl: 3}
    - {address: 10.0.51.1, rtt: 0.11024904251098633, ttl: 4}
    - {address: 151.7.21.65, rtt: 0.13367295265197754, ttl: 5}
    - {address: 151.7.8.69, rtt: 0.14918303489685059, ttl: 6}
    - {address: 151.6.4.206, rtt: 0.15334486961364746, ttl: 7}
    - {address: 151.6.1.142, rtt: 0.1617579460144043, ttl: 8}
    hops_23:
    - {address: 192.168.2.1, rtt: 0.01584005355834961, ttl: 1}
    - {address: 192.168.1.1, rtt: 0.02497100830078125, ttl: 2}
    - {address: 151.23.226.45, rtt: 0.04436492919921875, ttl: 3}
    - {address: 10.0.51.1, rtt: 0.061604976654052734, ttl: 4}
    - {address: 151.7.21.65, rtt: 0.07576203346252441, ttl: 5}
    - {address: 151.7.8.69, rtt: 0.08328104019165039, ttl: 6}
    - {address: 151.6.1.142, rtt: 0.10766100883483887, ttl: 7}
    - {address: 151.6.4.206, rtt: 0.15076494216918945, ttl: 8}
    hops_443:
    - {address: 192.168.2.1, rtt: 0.012732982635498047, ttl: 1}
    - {address: 192.168.1.1, rtt: 0.02148294448852539, ttl: 2}
    - {address: 151.23.226.45, rtt: 0.03827404975891113, ttl: 3}
    - {address: 10.0.51.1, rtt: 0.04786992073059082, ttl: 4}
    - {address: 151.7.21.65, rtt: 0.07964706420898438, ttl: 5}
    - {address: 151.7.8.69, rtt: 0.08100605010986328, ttl: 6}
    - {address: 151.6.4.206, rtt: 0.08287692070007324, ttl: 7}
    - {address: 151.6.1.142, rtt: 0.08915400505065918, ttl: 8}
    hops_80:
    - {address: 192.168.2.1, rtt: 0.023320913314819336, ttl: 1}
    - {address: 192.168.1.1, rtt: 0.04503607749938965, ttl: 2}
    - {address: 151.23.226.45, rtt: 0.05919003486633301, ttl: 3}
    - {address: 10.0.51.1, rtt: 0.07173705101013184, ttl: 4}
    - {address: 151.7.21.65, rtt: 0.08269405364990234, ttl: 5}
    - {address: 151.7.8.69, rtt: 0.08826589584350586, ttl: 6}
    - {address: 151.6.4.206, rtt: 0.09608697891235352, ttl: 7}
    - {address: 151.6.1.142, rtt: 0.11581897735595703, ttl: 8}
    max_ttl: 30
    sent_packets:
    - - raw_packet: !!binary |
          RQAAKKKkAAABBogbfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    - - raw_packet: !!binary |
          RQAAKDyvAAACBu0QfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    - - raw_packet: !!binary |
          RQAAKB9lAAADBglbfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    - - raw_packet: !!binary |
          RQAAKF69AAAEBskCfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    - - raw_packet: !!binary |
          RQAAKKLjAAAFBoPcfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    - - raw_packet: !!binary |
          RQAAKAF2AAAGBiRKfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    - - raw_packet: !!binary |
          RQAAKNjxAAAHBkvOfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    - - raw_packet: !!binary |
          RQAAKKlkAAAIBnpbfwAAAQgICAgAFAG7AAAAAAAAAABQAiAA/wIAAA==
        summary: IP / TCP 127.0.0.1:ftp_data > 8.8.8.8:https S
    timeout: 5
  test_name: test_tcp_traceroute
  test_started: 1353425277.715115
  ...
  ---
  input: null
  report:
    answered_packets:
    - - raw_packet: !!binary |
          RcAAOHvVAABAAXicwKgCAX8AAAELAPT/AAAAAEUAABxwTAAAAQF2m8CoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 192.168.2.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAOAhjQAA/Aa7OwKgBAX8AAAELAPT/AAAAAEUAABy0+wAAAQEx7MCoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 192.168.1.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RcAAOCe5AAD9AVkclxfiLX8AAAELAPT/AAAAAEUAABzKAQAAAQEc5sCoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 151.23.226.45 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RcAAOFScAAD8AWl9CgAzAX8AAAELAPT/AAAAAEUAABwJNAAAAQHds8CoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 10.0.51.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RcAAOKV+AAD7AapTlwcVQX8AAAELAPT/AAAAAEUAABzDBAAAAQEj48CoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 151.7.21.65 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAOB/cAAD6AT6ylwcIRX8AAAELAPT+AAAAAUUAABwDzwAAAQHjGMCoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 151.7.8.69 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD4AWQGlwYEzn8AAAELAPT/AAAAAEUAABxKAAAAAQGc58CoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 151.6.4.206 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD3AWhKlwYBin8AAAELAPT/AAAAAEUAABxVjgAAAQGRWcCoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 151.6.1.138 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD3AWm6lwYAGn8AAAELAPT/AAAAAEUAABwtmwAAAQG5TMCoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 151.6.0.26 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD1AThO0VX5Nn8AAAELAPT/AAAAAEWAABw0YgAAAQGyBcCoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 209.85.249.54 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAqK+LQADzAeSDSA7oTH8AAAELAPT/AAAAAEWAABwAkwAAAQHl1MCoAkIICAgICAD3/wAAAAAA
          AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
          AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIACbFAAIAQF64MkB
        summary: IP / ICMP 72.14.232.76 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror / Padding
    - - raw_packet: !!binary |
          RQAAOAAAAAD0ATQQ0VX+dH8AAAELAPT/AAAAAEWAABwVTAAAAQHRG8CoAkIICAgICAD3/wAAAAA=
        summary: IP / ICMP 209.85.254.116 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    - - raw_packet: !!binary |
          RQAAHCqxAAAtAZA2CAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCqyAAAtAZA1CAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCqzAAAtAZA0CAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq0AAAtAZAzCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq1AAAtAZAyCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq2AAAtAZAxCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq3AAAtAZAwCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq4AAAtAZAvCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq5AAAtAZAuCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq6AAAtAZAtCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq7AAAtAZAsCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq8AAAtAZArCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq9AAAtAZAqCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq+AAAtAZApCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCq/AAAtAZAoCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCrAAAAtAZAnCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    - - raw_packet: !!binary |
          RQAAHCrBAAAtAZAmCAgICH8AAAEAAAAAAAAAAA==
        summary: IP / ICMP 8.8.8.8 > 127.0.0.1 echo-reply 0
    hops:
    - {address: 192.168.2.1, rtt: 0.02021312713623047, ttl: 1}
    - {address: 192.168.1.1, rtt: 0.03769707679748535, ttl: 2}
    - {address: 151.23.226.45, rtt: 0.05884099006652832, ttl: 3}
    - {address: 10.0.51.1, rtt: 0.06669998168945312, ttl: 4}
    - {address: 151.7.21.65, rtt: 0.08714413642883301, ttl: 5}
    - {address: 151.7.8.69, rtt: 0.10510706901550293, ttl: 6}
    - {address: 151.6.4.206, rtt: 0.11643505096435547, ttl: 7}
    - {address: 151.6.1.138, rtt: 0.12979793548583984, ttl: 8}
    - {address: 151.6.0.26, rtt: 0.16455411911010742, ttl: 9}
    - {address: 209.85.249.54, rtt: 0.17022013664245605, ttl: 10}
    - {address: 72.14.232.76, rtt: 0.21141505241394043, ttl: 11}
    - {address: 209.85.254.116, rtt: 0.22271299362182617, ttl: 12}
    - {address: 8.8.8.8, rtt: 0.2633399963378906, ttl: 13}
    - {address: 8.8.8.8, rtt: 0.2839341163635254, ttl: 14}
    - {address: 8.8.8.8, rtt: 0.29700398445129395, ttl: 15}
    - {address: 8.8.8.8, rtt: 0.3080580234527588, ttl: 16}
    - {address: 8.8.8.8, rtt: 0.31791210174560547, ttl: 17}
    - {address: 8.8.8.8, rtt: 0.34924912452697754, ttl: 18}
    - {address: 8.8.8.8, rtt: 0.35537195205688477, ttl: 19}
    - {address: 8.8.8.8, rtt: 0.3696310520172119, ttl: 20}
    - {address: 8.8.8.8, rtt: 0.3782229423522949, ttl: 21}
    - {address: 8.8.8.8, rtt: 0.39800405502319336, ttl: 22}
    - {address: 8.8.8.8, rtt: 0.4051640033721924, ttl: 23}
    - {address: 8.8.8.8, rtt: 0.4123039245605469, ttl: 24}
    - {address: 8.8.8.8, rtt: 0.42334413528442383, ttl: 25}
    - {address: 8.8.8.8, rtt: 0.43251705169677734, ttl: 26}
    - {address: 8.8.8.8, rtt: 0.4546849727630615, ttl: 27}
    - {address: 8.8.8.8, rtt: 0.4642460346221924, ttl: 28}
    - {address: 8.8.8.8, rtt: 0.47597813606262207, ttl: 29}
    max_ttl: 30
    sent_packets:
    - - raw_packet: !!binary |
          RQAAHHBMAAABAbqEfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHLT7AAACAXTVfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHMoBAAADAV7PfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHAk0AAAEAR6dfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHMMEAAAFAWPMfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHAPPAAAGASICfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHEoAAAAHAdrQfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHFWOAAAIAc5CfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHC2bAAAJAfU1fwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHDRiAAAKAe1ufwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHACTAAALASA+fwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHBVMAAAMAQqFfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHBWnAAANAQkqfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHE26AAAOAdAWfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHMFeAAAPAVtyfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHMLoAAAQAVjofwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHGR2AAARAbZafwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHIjLAAASAZEFfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHD+rAAATAdklfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHNMmAAAUAUSqfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHMW8AAAVAVEUfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHN5MAAAWATeEfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHE3KAAAXAccGfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHMyzAAAYAUcdfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHCdWAAAZAet6fwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHBguAAAaAfmifwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHHPpAAAbAZznfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHDM1AAAcAdybfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    - - raw_packet: !!binary |
          RQAAHCPeAAAdAeryfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    timeout: 5
  test_name: test_icmp_traceroute
  test_started: 1353425284.345713
  ...
  ---
  input: null
  report:
    answered_packets:
    - - raw_packet: !!binary |
          RcAAOHvZAABAAXiYwKgCAX8AAAELAMgTAAAAAEUAABwx6gAAARG07cCoAkIICAgIADUAewAILDQ=
        summary: IP / ICMP 192.168.2.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    - - raw_packet: !!binary |
          RQAAOAhkAAA/Ae7NwKgBAX8AAAELAMgTAAAAAEUAABzc/wAAAREJ2MCoAkIICAgIADUAewAILDQ=
        summary: IP / ICMP 192.168.1.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    - - raw_packet: !!binary |
          RcAAOCjAAAD9AVgVlxfiLX8AAAELAMgTAAAAAEUAABwxrAAAARG1K8CoAkIICAgIADUAewAILDQ=
        summary: IP / ICMP 151.23.226.45 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    - - raw_packet: !!binary |
          RcAAOKYWAAD7Aam7lwcVQX8AAAELAMgTAAAAAEUAABwwvQAAARG2GsCoAkIICAgIADUAewAILDQ=
        summary: IP / ICMP 151.7.21.65 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    - - raw_packet: !!binary |
          RQAAOCSLAAD6AToDlwcIRX8AAAELAMgSAAAAAUUAABxthAAAARF5U8CoAkIICAgIADUAewAILDQ=
        summary: IP / ICMP 151.7.8.69 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD4AWQGlwYEzn8AAAELAMgTAAAAAEUAABytOgAAARE5ncCoAkIICAgIADUAewAILDQ=
        summary: IP / ICMP 151.6.4.206 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    - - raw_packet: !!binary |
          RQAAOAAAAAD3AWhGlwYBjn8AAAELAMgTAAAAAEUAABx29QAAARFv4sCoAkIICAgIADUAewAILDQ=
        summary: IP / ICMP 151.6.1.142 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    hops_123:
    - {address: 192.168.2.1, rtt: 0.005973100662231445, ttl: 1}
    - {address: 192.168.1.1, rtt: 0.01427006721496582, ttl: 2}
    - {address: 151.23.226.45, rtt: 0.02519512176513672, ttl: 3}
    - {address: 151.7.21.65, rtt: 0.028814077377319336, ttl: 4}
    - {address: 151.7.8.69, rtt: 0.03263592720031738, ttl: 5}
    - {address: 151.6.4.206, rtt: 0.036956071853637695, ttl: 6}
    - {address: 151.6.1.142, rtt: 0.040396928787231445, ttl: 7}
    hops_22:
    - {address: 192.168.2.1, rtt: 0.003320932388305664, ttl: 1}
    - {address: 151.23.226.45, rtt: 0.017846107482910156, ttl: 2}
    - {address: 10.0.51.1, rtt: 0.022522926330566406, ttl: 3}
    - {address: 151.7.21.65, rtt: 0.02526092529296875, ttl: 4}
    - {address: 151.7.8.69, rtt: 0.027420997619628906, ttl: 5}
    - {address: 151.6.4.206, rtt: 0.028680086135864258, ttl: 6}
    - {address: 151.6.1.142, rtt: 0.030663013458251953, ttl: 7}
    hops_23:
    - {address: 192.168.2.1, rtt: 0.0060520172119140625, ttl: 1}
    - {address: 151.23.226.45, rtt: 0.021609067916870117, ttl: 2}
    - {address: 10.0.51.1, rtt: 0.02601790428161621, ttl: 3}
    - {address: 151.7.21.65, rtt: 0.03017401695251465, ttl: 4}
    - {address: 151.7.8.69, rtt: 0.04059290885925293, ttl: 5}
    - {address: 151.6.4.206, rtt: 0.046777963638305664, ttl: 6}
    - {address: 151.6.1.142, rtt: 0.051110029220581055, ttl: 7}
    hops_443:
    - {address: 192.168.2.1, rtt: 0.0060040950775146484, ttl: 1}
    - {address: 151.23.226.45, rtt: 0.016175031661987305, ttl: 2}
    - {address: 10.0.51.1, rtt: 0.019622087478637695, ttl: 3}
    - {address: 151.7.21.65, rtt: 0.024995088577270508, ttl: 4}
    - {address: 151.7.8.69, rtt: 0.029528141021728516, ttl: 5}
    - {address: 151.6.4.206, rtt: 0.04129600524902344, ttl: 6}
    - {address: 151.6.1.142, rtt: 0.045397043228149414, ttl: 7}
    hops_80:
    - {address: 192.168.2.1, rtt: 0.01238107681274414, ttl: 1}
    - {address: 151.23.226.45, rtt: 0.022581100463867188, ttl: 2}
    - {address: 10.0.51.1, rtt: 0.024456024169921875, ttl: 3}
    - {address: 151.7.21.65, rtt: 0.03365302085876465, ttl: 4}
    - {address: 151.7.8.69, rtt: 0.04121208190917969, ttl: 5}
    - {address: 151.6.4.206, rtt: 0.043180227279663086, ttl: 6}
    - {address: 151.6.1.142, rtt: 0.05482816696166992, ttl: 7}
    max_ttl: 30
    sent_packets:
    - - raw_packet: !!binary |
          RQAAHDHqAAABEfjWfwAAAQgICAgANQB7AAhwHQ==
        summary: IP / UDP 127.0.0.1:domain > 8.8.8.8:ntp
    - - raw_packet: !!binary |
          RQAAHNz/AAACEUzBfwAAAQgICAgANQB7AAhwHQ==
        summary: IP / UDP 127.0.0.1:domain > 8.8.8.8:ntp
    - - raw_packet: !!binary |
          RQAAHDGsAAADEfcUfwAAAQgICAgANQB7AAhwHQ==
        summary: IP / UDP 127.0.0.1:domain > 8.8.8.8:ntp
    - - raw_packet: !!binary |
          RQAAHDC9AAAEEfcDfwAAAQgICAgANQB7AAhwHQ==
        summary: IP / UDP 127.0.0.1:domain > 8.8.8.8:ntp
    - - raw_packet: !!binary |
          RQAAHG2EAAAFEbk8fwAAAQgICAgANQB7AAhwHQ==
        summary: IP / UDP 127.0.0.1:domain > 8.8.8.8:ntp
    - - raw_packet: !!binary |
          RQAAHK06AAAGEXiGfwAAAQgICAgANQB7AAhwHQ==
        summary: IP / UDP 127.0.0.1:domain > 8.8.8.8:ntp
    - - raw_packet: !!binary |
          RQAAHHb1AAAHEa3LfwAAAQgICAgANQB7AAhwHQ==
        summary: IP / UDP 127.0.0.1:domain > 8.8.8.8:ntp
    timeout: 5
  test_name: test_udp_traceroute
  test_started: 1353425289.47829
  ...


TODO
====

 * Add IP flag to get the MPLS VRF number of the Hop (if it exists)

 * Activate IP option 7 record route


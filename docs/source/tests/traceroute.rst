Details
=======

*Test Name*: Traceroute

*Current version*: 0.1.1

*NetTest*: Traceroute (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/core/traceroute.py)

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
received in userspace via the scapy super socket that relies on libpcap and
libdnet.

Notes:

If the user states their privacy settings that they do not wish to include
their IP address in the report then the src IP address of sent packets and the
dst address of received packets is replaced with 127.0.0.1 (This feature is
of the scapy test template). In this case, though, user data is leaked through
other means that are not the src and destination IP address.

In particular the ICMP TTL expired citations will contain the IP headers.

We could theoretically strip these though even if that were the case there would
still be at least a reduction of the anonymity set given by the fact that we
received a TTL expired from a router in a certain network range.

How to run the test
===================

`ooniprobe nettests/manipulation/traceroute.py -b <backend ip>``

*backend ip* is the IP address of the backend to traceroute to

Sample report
=============

From running:

`ooniprobe nettests/core/traceroute.py -b 8.8.8.8`

::

  ###########################################
  # OONI Probe Report for Multi Protocol Traceroute Test test
  # Thu Nov 29 20:07:00 2012
  ###########################################
  ---
  options:
    collector: null
    help: 0
    logfile: null
    pcapfile: null
    reportfile: null
    resume: 0
    subargs: [-b, 8.8.8.8]
    test: nettests/manipulation/traceroute.py
  probe_asn: null
  probe_cc: null
  probe_ip: 127.0.0.1
  software_name: ooniprobe
  software_version: 0.0.7.1-alpha
  start_time: 1354212420.0
  test_name: Multi Protocol Traceroute Test
  test_version: 0.1.1
  ...
  ---
  input: null
  report:
    answer_flags: [ipsrc]
    answered_packets:
    - - raw_packet: !!binary |
          RQAAOAOrAABAAdNUwKgRAX8AAAELAC9XAAAAAEUAACgbGgAAAQa8isCoEXQICAgIxZIAFgAAAAAA
          AAAAUAIgAOgNAAA=
        summary: IP / ICMP 192.168.17.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / TCPerror
    hops_123:
    - {address: 192.168.17.1, rtt: 0.6290309429168701, sport: 1234, ttl: 1}
    hops_22:
    - {address: 192.168.17.1, rtt: 0.5726521015167236, sport: 1234, ttl: 1}
    hops_23:
    - {address: 192.168.17.1, rtt: 0.5733599662780762, sport: 1234, ttl: 1}
    hops_443:
    - {address: 192.168.17.1, rtt: 0.6443209648132324, sport: 1234, ttl: 1}
    hops_53:
    - {address: 192.168.17.1, rtt: 0.5956859588623047, sport: 1234, ttl: 1}
    hops_80:
    - {address: 192.168.17.1, rtt: 0.615354061126709, sport: 1234, ttl: 1}
    max_ttl: 30
    sent_packets:
    - - raw_packet: !!binary |
          RQAAKBsaAAABBg+mfwAAAQgICAjFkgAWAAAAAAAAAABQAiAAOykAAA==
        summary: IP / TCP 127.0.0.1:50578 > 8.8.8.8:ssh S
      timeout: 5
  test_name: test_tcp_traceroute
  test_runtime: 5.283383131027222
  test_started: 1354216020.235762
  ...
  ---
  input: null
  report:
    answer_flags: [ipsrc]
    answered_packets:
    - - raw_packet: !!binary |
          RQAAOAOxQABAAZNOwKgRAX8AAAELAPT/AAAAAEUAAByhTwAAAQE2ZsCoEXQICAgICAD3/wAAAAA=
        summary: IP / ICMP 192.168.17.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / ICMPerror
    hops:
    - {address: 192.168.17.1, rtt: 0.6631519794464111, ttl: 1}
    max_ttl: 30
    sent_packets:
    - - raw_packet: !!binary |
          RQAAHKFPAAABAYmBfwAAAQgICAgIAPf/AAAAAA==
        summary: IP / ICMP 127.0.0.1 > 8.8.8.8 echo-request 0
    timeout: 5
  test_name: test_icmp_traceroute
  test_runtime: 5.753404140472412
  test_started: 1354216020.515606
  ...
  ---
  input: null
  report:
    answer_flags: [ipsrc]
    answered_packets:
    - - raw_packet: !!binary |
          RQAAOAOyAABAAdNNwKgRAX8AAAELANdFAAAAAEUAABzRVQAAAREGUMCoEXQICAgItO4AFgAIaK0=
        summary: IP / ICMP 192.168.17.1 > 127.0.0.1 time-exceeded ttl-zero-during-transit
          / IPerror / UDPerror
    hops_123:
    - {address: 192.168.17.1, rtt: 1.471999168395996, sport: 22958, ttl: 1}
    hops_22:
    - {address: 192.168.17.1, rtt: 0.698897123336792, sport: 46318, ttl: 1}
    hops_23:
    - {address: 192.168.17.1, rtt: 0.9357340335845947, sport: 10580, ttl: 1}
    hops_443:
    - {address: 192.168.17.1, rtt: 1.6294240951538086, sport: 50104, ttl: 1}
    hops_53:
    - {address: 192.168.17.1, rtt: 1.1403398513793945, sport: 62061, ttl: 1}
    hops_80:
    - {address: 192.168.17.1, rtt: 1.328758955001831, sport: 23760, ttl: 1}
    max_ttl: 30
    sent_packets:
    - - raw_packet: !!binary |
          RQAAHNFVAAABEVlrfwAAAQgICAi07gAWAAi7yA==
        summary: IP / UDP 127.0.0.1:46318 > 8.8.8.8:ssh
      timeout: 5
  test_name: test_udp_traceroute
  test_runtime: 6.669445991516113
  test_started: 1354216020.561038
  ...

TODO
====

 * Add IP flag to get the MPLS VRF number of the Hop (if it exists)

 * Activate IP option 7 record route


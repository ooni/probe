Details
=======

*Test Name*: Bridge Reachability Test

*Current version*: 0.1.2

*NetTest*: HTTP Requests (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/blocking/bridge_reachability.py)

*Test Helper*: None

*Test Type*: Content Blocking

*Requires Root*: No

Description
===========

This test detects which Tor bridges are working from the given network vantage
point and which ones are not. For every bridge specified as input a new tor
instance is started and it is instructed to connect to Tor using that bridge.
It will try to bootstrap to 100% and either succeed or timeout after a default
time of 120 seconds.

How to run the test
===================

`ooniprobe blocking/bridge_reachability.py -f <input_file>`

*input file* a list of TransportType IP:ORPort bridges (ex. obfs3
198.51.100.45:9045) or IP:ORPort (ex. 203.0.113.27:1828) to test reachability
for.

Optional test options
=====================

*-t* Specify the timeout after which to consider the Tor bootstrapping process
to have failed. The default is 120 seconds.

Sample report
=============

`ooniprobe blocking/bridge_reachability.py -f bridges.txt`

::

###########################################
# OONI Probe Report for bridge_reachability (0.1)
# Thu Aug  7 16:10:50 2014
###########################################
---
input_hashes: [595c8ad9b63ff9f142eca6296021990df6367ab03b3c4eb1c69a8747f0cd41a1]
options: [-f, bridges.txt]
probe_asn: AS3269
probe_cc: IT
probe_city: null
probe_ip: 127.0.0.1
software_name: ooniprobe
software_version: 1.0.2
start_time: 1407420650.560137
test_name: bridge_reachability
test_version: '0.1'
...
---
{bridge_address: '169.229.59.74:31493', error: null, input: 'obfs3 169.229.59.74:31493
    AF9F66B7B04F8FF6F32D455F05135250A16543C9', success: true, timeout: 120, tor_log: null,
  tor_progress: 100, tor_progress_summary: Done, tor_progress_tag: done, tor_version: 0.2.4.20,
  transport_name: obfs3}
...
---
{bridge_address: '169.229.59.75:46328', error: null, input: 'obfs3 169.229.59.75:46328
    AF9F66B7B04F8FF6F32D455F05135250A16543C9', success: true, timeout: 120, tor_log: null,
  tor_progress: 100, tor_progress_summary: Done, tor_progress_tag: done, tor_version: 0.2.4.20,
  transport_name: obfs3}
...
---
{bridge_address: '208.79.90.242:35658', error: null, input: 'obfs3 208.79.90.242:35658
    BA61757846841D64A83EA2514C766CB92F1FB41F', success: true, timeout: 120, tor_log: null,
  tor_progress: 100, tor_progress_summary: Done, tor_progress_tag: done, tor_version: 0.2.4.20,
  transport_name: obfs3}
...
---
{bridge_address: '83.212.100.216:47870', error: null, input: 'obfs2 83.212.100.216:47870
    1F01A7BB60F49FC96E0850A6BAD6D076DFEFAF80', success: false, timeout: 120, tor_log: '',
  tor_progress: 0, tor_progress_summary: null, tor_progress_tag: null, tor_version: 0.2.4.20,
  transport_name: obfs2}
...
---
{bridge_address: '83.212.96.182:46602', error: null, input: 'obfs2 83.212.96.182:46602
    6F058CBEF888EB20D1DEB9886909F1E812245D41', success: false, timeout: 120, tor_log: '',
  tor_progress: 0, tor_progress_summary: null, tor_progress_tag: null, tor_version: 0.2.4.20,
  transport_name: obfs2}
...
---
{bridge_address: '70.182.182.109:54542', error: null, input: 'obfs2 70.182.182.109:54542
    94C9E691688FAFDEC701A0788BD15BE8AD34ED35', success: false, timeout: 120, tor_log: '',
  tor_progress: 0, tor_progress_summary: null, tor_progress_tag: null, tor_version: 0.2.4.20,
  transport_name: obfs2}
...
---
{bridge_address: '128.31.0.34:1051', error: null, input: 'obfs2 128.31.0.34:1051 CA7434F14A898C7D3427B8295A7F83446BC7F496',
  success: false, timeout: 120, tor_log: '', tor_progress: 0, tor_progress_summary: null,
  tor_progress_tag: null, tor_version: 0.2.4.20, transport_name: obfs2}
...
---
{bridge_address: '83.212.101.2:45235', error: null, input: 'obfs2 83.212.101.2:45235
    2ADFE7AA8D272C520D1FBFBF4E413F3A1B26313D', success: false, timeout: 120, tor_log: '',
  tor_progress: 0, tor_progress_summary: null, tor_progress_tag: null, tor_version: 0.2.4.20,
  transport_name: obfs2}
...
---
{bridge_address: '83.212.101.2:42782', error: null, input: 'obfs3 83.212.101.2:42782
    2ADFE7AA8D272C520D1FBFBF4E413F3A1B26313D', success: false, timeout: 120, tor_log: '',
  tor_progress: 0, tor_progress_summary: null, tor_progress_tag: null, tor_version: 0.2.4.20,
  transport_name: obfs3}
...
---
{bridge_address: '83.212.101.2:443', error: null, input: 'obfs3 83.212.101.2:443 2ADFE7AA8D272C520D1FBFBF4E413F3A1B26313D',
  success: false, timeout: 120, tor_log: '', tor_progress: 0, tor_progress_summary: null,
  tor_progress_tag: null, tor_version: 0.2.4.20, transport_name: obfs3}
...
---
{bridge_address: '209.141.36.236:45496', error: null, input: 'obfs3 209.141.36.236:45496
    58D91C3A631F910F32E18A55441D5A0463BA66E2', success: false, timeout: 120, tor_log: '',
  tor_progress: 0, tor_progress_summary: null, tor_progress_tag: null, tor_version: 0.2.4.20,
  transport_name: obfs3}
...
    ...


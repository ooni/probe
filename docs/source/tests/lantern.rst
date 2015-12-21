Details
=======

*Test Name*: Lantern

*Current version*: 0.0.1

*NetTest*: Name (https://github.com/TheTorProject/ooni-probe/blob/master/ooni/nettests/third_party/lantern.py)

*Test Helper*: None

*Test Type*: Third Party

*Requires Root*: No

Description
===========

This test launches Lantern in --headless mode, and parses output to determine
if it has bootstrapped.  After bootstrap, it fetches the URL supplied by the
--url option using Lanterns http proxy interface listening on 127.0.0.1.8787.

The specific string used to determine bootstrap from Lantern output in version
"2.0.10" is "client (http) proxy at" from standard output.

How to run the test
===================

`ooniprobe nettests/third_party/lantern.py -u http://<url>`

Sample report
=============

From running:
`ooniprobe nettests/third_party/lantern.py -u http://www.google.com`

::

---
input_hashes: []
options: [-u, google.com]
probe_asn: AS1234
probe_cc: US
probe_city: null
probe_ip: 127.0.0.1
software_name: ooniprobe
software_version: 1.2.3-rc1
start_time: 1428344311.0
test_name: lantern_circumvention_tool_test
test_version: 0.0.1
...
---
body: "<HTML><HEAD><meta http-equiv=\"content-type\" content=\"text/html;charset=utf-8\"\
  >\n<TITLE>301 Moved</TITLE></HEAD><BODY>\n<H1>301 Moved</H1>\nThe document has moved\n\
  <A HREF=\"http://www.google.com/\">here</A>.\r\n</BODY></HTML>\r\n"
bootstrapped: true
input: null
lantern --headless: {exit_reason: process_done, stderr: '', stdout: ''}
```


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
if it has bootstrapped.  After bootstrap, it fetches a URL using Lanterns HTTP
proxy interface listening on 127.0.0.1.8787 and checks to see if the response
body matches the expected result.
As a URL for testing we use http://www.google.com/humans.txt and look for the
string "Google is built by a large" in the response body.

The specific string used to determine bootstrap from Lantern output in version
"2.0.10" is "Successfully dialed via" from standard output.

How to run the test
===================

`ooniprobe nettests/third_party/lantern.py`

For advanced usages you may also configure a different URL and expected body
for the response with the `--url` and `--expected-body` command line options.

`ooniprobe nettests/third_party/lantern.py --url http://humanstxt.org/humans.txt --expected-body '/* TEAM */'`

Sample report
=============

From running:
`ooniprobe nettests/third_party/lantern.py`

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
body: "Google is built by a large team of engineers, designers, researchers, robots, and others in many different sites across the globe. It is updated continuously, and built with more tools and technologies than we can shake a stick at. If you'd like to help us out, see google.com/careers."
bootstrapped: true
default_configuration: true
input: null
lantern --headless: {exit_reason: process_done, stderr: '', stdout: ''}
```


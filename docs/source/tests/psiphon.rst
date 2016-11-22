Details
=======

*Test Name*: Psiphon

*Current version*: 0.1

*NetTest*: Psiphon (https://github.com/TheTorProject/ooni-probe/blob/master/ooni/nettests/third_party/psiphon.py)

*Test Helper*: None

*Test Type*: third party

*Requires Root*: No

Description
===========

This test first check that the Psiphon path exists, then launches Psiphon and
parses output to determine if it has bootstrapped. After bootstrap, it fetches
`http://www.google.com/humans.txt` using Psiphons SOCKS
proxy listening on 127.0.0.1:1080 (or otherwise specified by the --socksproxy
argument).
It will then check to see if the response body contains the string: "Google is built by a large"

The specific string used to determine bootstrap from Psiphon output in version
"0.0.1" is "Press Ctrl-C to terminate." from standard output.

How to run the test
===================

`ooniprobe third_party/psiphon`

To test Psiphon when it is installed in a different path other than the user home:

`ooniprobe third_party/psiphon -p <path to Psiphon repository>`

For advanced usages you may also configure a different URL and expected body
for the response with the `--url` and `--expected-body` command line options.

`ooniprobe third_party/psiphon --url http://www.github.com/humans.txt --expected-body '/* TEAM */'`


How to install Psiphon
===================

Run the install script:

`scripts/psiphon_install.sh`

To run Psiphon manually, it must be run inside of the proper directory:

`cd <psiphonpath>//psiphon-circumvention-system/pyclient/`
`python psi_client.py`

Sample report
=============

`ooniprobe third_party/psiphon`

    ::

    ###########################################
    # OONI Probe Report for psiphon_test (0.0.1)
    # Mon Oct 12 21:40:52 2015
    ###########################################
    ---
    input_hashes: []
    options: [-u, google.com]
    probe_asn: AS0
    probe_cc: ZZ
    probe_city: null
    probe_ip: 127.0.0.1
    report_id: 4dAHr0ceNDBmw5lUQ7pBoxqgyUSfP873Qj1zv5VyElnSSTXwcsLYeCv69DsUjb94
    software_name: ooniprobe
    software_version: 1.3.1
    start_time: 1444686051.0
    test_helpers: {}
    test_name: psiphon_test
    test_version: 0.0.1
    ...
    ---
    /tmp/tmplKg8K3: {exit_reason: process_done, stderr: '', stdout: "./ssh is not a valid\
        \ executable. Using standard ssh.\r\n\r\nYour SOCKS proxy is now running at 127.0.0.1:1080\r\
        \n\r\nPress Ctrl-C to terminate.\r\nTerminating...\r\nConnection closed\r\n"}
    agent: agent
    input: null
    psiphon_installed: true
    default_configuration: true
    requests:
    - request:
        body: null
        headers: []
        method: GET
        tor: {is_tor: false}
        url: http://google.com
      response:
        body: "Google is built by a large team of engineers, designers, researchers, robots, and others in many different sites across the globe. It is updated continuously, and built with more tools and technologies than we can shake a stick at. If you'd like to help us out, see google.com/careers."
        code: 301
        headers:
        - - Content-Length
          - ['219']
        - - X-XSS-Protection
          - [1; mode=block]
        - - Expires
          - ['Wed, 11 Nov 2015 21:40:58 GMT']
        - - Server
          - [gws]
        - - Connection
          - [close]
        - - Location
          - ['http://www.google.com/']
        - - Cache-Control
          - ['public, max-age=2592000']
        - - Date
          - ['Mon, 12 Oct 2015 21:40:58 GMT']
        - - X-Frame-Options
          - [SAMEORIGIN]
        - - Content-Type
          - [text/html; charset=UTF-8]
    socksproxy: 127.0.0.1:1080
    test_runtime: 7.373162031173706
    test_start_time: 1444686052.0
    ...


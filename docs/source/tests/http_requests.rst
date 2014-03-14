Details
=======

*Test Name*: HTTP Requests

*Current version*: 0.1

*NetTest*: HTTP Requests (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/blocking/http_requests.py)

*Test Helper*: None

*Test Type*: Content Blocking

*Requires Root*: No

Description
===========

This test perform a HTTP GET request for the / resource over the test network
and over Tor. It then compares the two responses to see if the response bodies of the two requests match and if the 
proportion between the expected body length (the one over Tor) and the one over
the control network match.

If the proportion between the two body lengths is <= a certain tolerance factor
(by default set to 0.8), then we say that they do not match.

The reason for doing so is that a lot of sites serve geolocalized content based
on the location from which the request originated from.

How to run the test
===================

To test a single site run:

`ooniprobe blocking/http_requests -u http://<test_site>/`

To test a set of sites from a list containing sites to test run:

`ooniprobe blocking/http_requests -f <input_file>`


Sample report
=============

`ooniprobe blocking/http_requests -f example_inputs/url_lists_file.txt`

::

    ###########################################
    # OONI Probe Report for HTTP Requests Test test
    # Thu Nov 29 13:20:06 2012
    ###########################################
    ---
    options:
      collector: null
      help: 0
      logfile: null
      pcapfile: null
      reportfile: null
      resume: 0
      subargs: [-f, example_inputs/url_lists_file.txt]
      test: nettests/blocking/http_requests.py
    probe_asn: null
    probe_cc: null
    probe_ip: 127.0.0.1
    software_name: ooniprobe
    software_version: 0.0.7.1-alpha
    start_time: 1354188006.0
    test_name: HTTP Requests Test
    test_version: '0.1'
    ...
    ---
    input: http://ooni.nu/test
    report:
      agent: agent
      body_length_match: false
      body_proportion: 0.9732142857142857
      factor: 0.8
      requests:
      - request:
          body: null
          headers:
          - - User-Agent
            - - &id001 [Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1), 'Internet
                  Explorer 7, Windows Vista']
          method: GET
          url: http://ooni.nu/test
        response:
          body: "\n<html>\n    <head>\n        <meta http-equiv=\"refresh\" content=\"\
            0;URL=http://ooni.nu/test/\">\n    </head>\n    <body bgcolor=\"#FFFFFF\"\
            \ text=\"#000000\">\n    <a href=\"http://ooni.nu/test/\">click here</a>\n\
            \    </body>\n</html>\n"
          code: 302
          headers:
          - - Content-Length
            - ['218']
          - - Server
            - [TwistedWeb/10.1.0]
          - - Connection
            - [close]
          - - Location
            - ['http://ooni.nu/test/']
          - - Date
            - ['Thu, 29 Nov 2012 12:20:25 GMT']
          - - Content-Type
            - [text/html]
      - request:
          body: null
          headers:
          - - User-Agent
            - - *id001
          method: GET
          url: shttp://ooni.nu/test
        response:
          body: "\n<html>\n    <head>\n        <meta http-equiv=\"refresh\" content=\"\
            0;URL=http://ooni.nu:80/test/\">\n    </head>\n    <body bgcolor=\"#FFFFFF\"\
            \ text=\"#000000\">\n    <a href=\"http://ooni.nu:80/test/\">click here</a>\n\
            \    </body>\n</html>\n"
          code: 302
          headers:
          - - Content-Length
            - ['224']
          - - Server
            - [TwistedWeb/10.1.0]
          - - Connection
            - [close]
          - - Location
            - ['http://ooni.nu:80/test/']
          - - Date
            - ['Thu, 29 Nov 2012 12:20:33 GMT']
          - - Content-Type
            - [text/html]
      socksproxy: null
    test_name: test_get
    test_runtime: 9.357746124267578
    test_started: 1354191606.333243
    ...
    ---
    input: http://torproject.org/
    report:
      agent: agent
      body_length_match: false
      body_proportion: 1.0
      factor: 0.8
      requests:
      - request:
          body: null
          headers:
          - - User-Agent
            - - &id001 [Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1), 'Internet
                  Explorer 7, Windows Vista']
          method: GET
          url: http://torproject.org/
        response:
          body: '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">

            <html><head>

            <title>302 Found</title>

            </head><body>

            <h1>Found</h1>

            <p>The document has moved <a href="https://www.torproject.org/">here</a>.</p>

            <hr>

            <address>Apache Server at torproject.org Port 80</address>

            </body></html>

            '
          code: 302
          headers:
          - - Content-Length
            - ['275']
          - - Vary
            - [Accept-Encoding]
          - - Server
            - [Apache]
          - - Connection
            - [close]
          - - Location
            - ['https://www.torproject.org/']
          - - Date
            - ['Thu, 29 Nov 2012 12:20:08 GMT']
          - - Content-Type
            - [text/html; charset=iso-8859-1]
      - request:
          body: null
          headers:
          - - User-Agent
            - - *id001
          method: GET
          url: shttp://torproject.org/
        response:
          body: '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">

            <html><head>

            <title>302 Found</title>

            </head><body>

            <h1>Found</h1>

            <p>The document has moved <a href="https://www.torproject.org/">here</a>.</p>

            <hr>

            <address>Apache Server at torproject.org Port 80</address>

            </body></html>

            '
          code: 302
          headers:
          - - Content-Length
            - ['275']
          - - Vary
            - [Accept-Encoding]
          - - Server
            - [Apache]
          - - Connection
            - [close]
          - - Location
            - ['https://www.torproject.org/']
          - - Date
            - ['Thu, 29 Nov 2012 12:20:16 GMT']
          - - Content-Type
            - [text/html; charset=iso-8859-1]
      socksproxy: null
    test_name: test_get
    test_runtime: 8.688138008117676
    test_started: 1354191607.287672
    ...


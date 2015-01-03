Details
=======

*Test Name*: HTTP Invalid Request Line

*Current version*: 0.1.3

*NetTest*: HTTP Invalid Request Line (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/manipulation/http_invalid_request_line.py)

*Test Helper*: TCPEchoHelper (https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/tcp_helpers.py)

*Test Type*: Traffic Manipulation

*Requires Root*: No

*WARNING*: This test is more dangerous to run than any other one and you
should do it only if you know what you are doing.

Description
===========

The goal of this test is to do some very basic and not very noisy fuzzing
on the HTTP request line. We generate a series of requests that are not
valid HTTP requests.

The remote backend runs a TCP echo server. If the response from the backend
does not match with what we have sent then we say that tampering is occurring.

The idea behind this is that certain transparent HTTP proxies may not be
properly parsing the HTTP request line.

Unless elsewhere stated 'Xx'\*N refers to N\*2 random upper or lowercase ascii
letters or numbers ('XxXx' will be 4).

What we fuzz is the following:

test random invalid method
**************************

This sends random 4 letter HTTP request method.

The request on the wire will look like this:

::
    XxXxX / HTTP/1.1\n\r


test random invalid field count
*******************************

This generates a request that looks like this:

::
    XxXxX XxXxX XxXxX XxXxX

    This may trigger some bugs in the HTTP parsers of transparent HTTP
    proxies.


test random big request method
******************************

This generates a request that looks like this:

::

    Xx*512 / HTTP/1.1


test random invalid version number
**********************************

This generates a request that looks like this:

::
    GET / HTTP/XxX

This attempts to trigger bugs in the parsing of the HTTP version number, that
is usually being split on the `.`.

How to run the test
===================

`ooniprobe nettests/manipulation/http_invalid_request_line.py -b <address of backend>`

*address of the backend* is the hostname or IP address of a backend that runs
a TCP echo server on port 80.

Sample report
=============

From running:

`ooniprobe nettests/manipulation/http_invalid_request_line.py -b 127.0.0.1 -p 57002`

::

    ###########################################
    # OONI Probe Report for HTTP Invalid Request Line test
    # Thu Nov 29 16:41:15 2012
    ###########################################
    ---
    options:
      collector: null
      help: 0
      logfile: null
      pcapfile: null
      reportfile: null
      resume: 0
      subargs: [-b, 127.0.0.1, -p, '57002']
      test: nettests/manipulation/http_invalid_request_line.py
    probe_asn: null
    probe_cc: null
    probe_ip: 127.0.0.1
    software_name: ooniprobe
    software_version: 0.0.7.1-alpha
    start_time: 1354200075.0
    test_name: HTTP Invalid Request Line
    test_version: 0.1.3
    ...
    ---
    input: null
    report:
      received: ["L3F6 / HTTP/1.1\n\r"]
      sent: ["L3F6 / HTTP/1.1\n\r"]
      tampering: false
    test_name: test_random_invalid_method
    test_runtime: 5.011919021606445
    test_started: 1354203675.481258
    ...
    ---
    input: null
    report:
      received: ["GET / HTTP/Ayo\n\r"]
      sent: ["GET / HTTP/Ayo\n\r"]
      tampering: false
    test_name: test_random_invalid_version_number
    test_runtime: 5.019288063049316
    test_started: 1354203675.48221
    ...
    ---
    input: null
    report:
      received: ["RZRcu OyLtu Jtu2T cs0ER\n\r"]
      sent: ["RZRcu OyLtu Jtu2T cs0ER\n\r"]
      tampering: false
    test_name: test_random_invalid_field_count
    test_runtime: 5.022854804992676
    test_started: 1354203675.483127
    ...
    ---
    input: null
    report:
      received: ["iB2HrwJeB512y5CrAAaIpETZ5RMprmGO4RCex24Kmqkjguc2XsOrGXR3qJIERw1IX13uGWVs1kOd96Y0zsR4ufcktGFnP0gYakTq7GA63rNNOmlG9tNXABnBEHfkHYhrwdrewAKdqZ2lGls66NBY7fbL9xkOsHBjXq7TkvS8MOeTb74wcxKymp1NLOa8u7C8XP9qpafQtWBrC4dkEVjppjlFyetg1tu8zomDUCBx9y2tB411d8lw7WOSMfDiQWG327aVanxaOj9WgZ2u2eu0595UiJxZxMk1LYa96vHvmB1DrX0DoJUkUg2fcEOlia3pVoFfcpbd3TQ0GwEoewU3F48Qvpf2AuOIcPgrYa1XszLCyUoToygc5J6WgIH7f1phsEpmmZ6my9KChZdnazc7mNbCwLB3Z1wMwcoFW1XuDvAhTr8OYoY17360SYkAqEBhYh8uiD4xdIq0T0KJzsJW5wghjCMjRjFyfk3wyDXaPLp7vkeeqbA3FNFatFQlUCTIkqqqM3EjAojynvCDVyrThGlmsauS9Ejhc9TaDojeT3s8HZY3KIDHwCRvpGgpwFie2NyhzmwY2y4YFMcnGXT2jlwsVE1K2fZZ7yGbKqbciuh5Q32JNvQBdGy3N63PWyZIxWhfythHOVBE9GXAr99DqEXUeiRkfNer5aVRt87rDBuLx13IrbCE6runHdoZEq0iXs7IySfw5qqt00fExbaN9UlSDyxyYIrIymrSTSUWWprTqiezn1toQZpxEl53pv4ZnLx00CSMYxWTzMDNSHLpovdAI9A27ugY2uHmPETKHbaLsTzNRtNiZAS9WidDi0oAxdICB47dnJA2CXvBaXeq2nsRasgQ9qqNl0RbTC8vhXgIq8nZZQn0iehXsP5mPXshpALyfAhoLwiChRif8FODkKdAgciLviTvyadpecb6HqRVfM8rLzMPkuXT2I21yB7NVQQLraJOeDOTvmtsV2gw2I2ON8xKtHO78VQfo357yBryndTQTRTk9FPnijwcwusn\
          \ / HTTP/1.1\n\r"]
      sent: ["iB2HrwJeB512y5CrAAaIpETZ5RMprmGO4RCex24Kmqkjguc2XsOrGXR3qJIERw1IX13uGWVs1kOd96Y0zsR4ufcktGFnP0gYakTq7GA63rNNOmlG9tNXABnBEHfkHYhrwdrewAKdqZ2lGls66NBY7fbL9xkOsHBjXq7TkvS8MOeTb74wcxKymp1NLOa8u7C8XP9qpafQtWBrC4dkEVjppjlFyetg1tu8zomDUCBx9y2tB411d8lw7WOSMfDiQWG327aVanxaOj9WgZ2u2eu0595UiJxZxMk1LYa96vHvmB1DrX0DoJUkUg2fcEOlia3pVoFfcpbd3TQ0GwEoewU3F48Qvpf2AuOIcPgrYa1XszLCyUoToygc5J6WgIH7f1phsEpmmZ6my9KChZdnazc7mNbCwLB3Z1wMwcoFW1XuDvAhTr8OYoY17360SYkAqEBhYh8uiD4xdIq0T0KJzsJW5wghjCMjRjFyfk3wyDXaPLp7vkeeqbA3FNFatFQlUCTIkqqqM3EjAojynvCDVyrThGlmsauS9Ejhc9TaDojeT3s8HZY3KIDHwCRvpGgpwFie2NyhzmwY2y4YFMcnGXT2jlwsVE1K2fZZ7yGbKqbciuh5Q32JNvQBdGy3N63PWyZIxWhfythHOVBE9GXAr99DqEXUeiRkfNer5aVRt87rDBuLx13IrbCE6runHdoZEq0iXs7IySfw5qqt00fExbaN9UlSDyxyYIrIymrSTSUWWprTqiezn1toQZpxEl53pv4ZnLx00CSMYxWTzMDNSHLpovdAI9A27ugY2uHmPETKHbaLsTzNRtNiZAS9WidDi0oAxdICB47dnJA2CXvBaXeq2nsRasgQ9qqNl0RbTC8vhXgIq8nZZQn0iehXsP5mPXshpALyfAhoLwiChRif8FODkKdAgciLviTvyadpecb6HqRVfM8rLzMPkuXT2I21yB7NVQQLraJOeDOTvmtsV2gw2I2ON8xKtHO78VQfo357yBryndTQTRTk9FPnijwcwusn\
          \ / HTTP/1.1\n\r"]
      tampering: false
    test_name: test_random_big_request_method
    test_runtime: 5.026142120361328
    test_started: 1354203675.484211
    ...



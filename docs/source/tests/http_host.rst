Details
=======

*Test Name*: HTTP Host

*Current version*: 0.2

*NetTest*: HTTP Host (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/core/http_host.py)

*Test Helper*: HTTP Return JSON Headers (https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/http_helpers.py)

*Test Type*: Traffic Manipulation, Content Blocking

*Requires Root*: No

Description
===========

This test is aimed at detecting the presence of a transparent HTTP proxy and
enumerating the sites that are being censored by it.

It places inside of the Host header field the hostname of the site that is to
be tested for censorship and then determines if the probe is behind a
transparent HTTP proxy (because the response from the backend server does not
match) and if the site is censored, by checking if the page that it got back
matches the input block page.

*Why do content blocking?*

Q: Why should be do content blocking measurements with this test when we have
other tests that also do this?

A: Why not? Although you are correct that technically the two tests are
equivalent even though the IP layer differs in the two tests.

Note: We may in the future remove the Content Blocking aspect of the HTTP Host
test.

How to run the test
===================

`ooniprobe nettest/core/http_host.py -f <input file> -b <backend url> -c <content>`

*input_file* is a file containing the hostnames to check for censorship one per line.

*backend url* is the url of the backend that will be used for checking if the
site is blocked or not.

*content* is the content of a page. When a transparent HTTP proxy is present we
will do comparisons against this to verify if the requested site is blocked or
not.


Sample report
=============

From running:
`ooniprobe nettests/core/http_host.py`

::

  ###########################################
  # OONI Probe Report for HTTP Host test
  # Tue Nov 20 17:42:50 2012
  ###########################################
  ---
  {probe_asn: null, probe_cc: null, probe_ip: 127.0.0.1, software_name: ooniprobe, software_version: 0.0.7.1-alpha,
    start_time: 1353426170.0, test_name: HTTP Host, test_version: '0.2'}
  ...
  ---
  input: torproject.org
  report:
    requests:
    - request:
        body: null
        headers:
          Host: [torproject.org]
          User-Agent:
          - ['Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.7.5) Gecko/20060127
              Netscape/8.1', 'Netscape 8.1, Windows XP']
        method: GET
        url: http://127.0.0.1:57001
      response:
        body: '{"request_method": "GET", "request_uri": "/", "request_body": "", "request_headers":
          {"Connection": "close", "Host": "torproject.org", "User-Agent": "(''Mozilla/5.0
          (Windows; U; Windows NT 5.1; en-US; rv:1.7.5) Gecko/20060127 Netscape/8.1'',
          ''Netscape 8.1, Windows XP'')"}}'
        code: 200
        headers:
        - - Content-Length
          - ['270']
        - - Etag
          - ['"83dd0f393b39d0a316b2fc61fd61dafa92c336b5"']
        - - Content-Type
          - [text/html; charset=UTF-8]
        - - Server
          - [cyclone/1.0-rc13]
    trans_http_proxy: false
  test_name: test_send_host_header
  test_started: 1353429770.287463
  ...


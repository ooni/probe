Details
=======

*Test Name*: HTTP Header Field Manipulation

*Current version*: 0.1.3

*NetTest*: HTTPHeaderFieldManipulation (https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/ooni/nettests/manipulation/http_header_field_manipulation.py)

*Test Helper*: HTTP Return JSON Headers (https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/http_helpers.py)

*Test Type*: Traffic Manipulation

*Requires Root*: No

Description
===========
It performes HTTP requests with request headers that vary capitalization
towards a HTTPReturnJSONHeaders test helper backend. If we detect that the
headers the backend received don't matche the ones we have sent then we have
detected tampering.

How to run the test
===================

`ooniprobe nettests/manipulation/http_header_field_manipulation.py -b <address of backend> [-h <headers>]`
`address of backend` is the IP:PORT of the SimpleHTTPChannel backend.

Sample report
=============

From running:
`ooniprobe nettests/manipulation/http_header_field_manipulation.py`
If no backend is specified, the default backend is 127.0.0.1:57001, where you will need to have oonib listening.

::

  ###########################################
  # OONI Probe Report for HTTP Header Field Manipulation test
  # Thu Dec  6 19:22:00 2012
  ###########################################
  ---
  options:
    collector: null
    help: 0
    logfile: null
    pcapfile: null
    reportfile: null
    resume: 0
    subargs: []
    test: nettests/manipulation/http_header_field_manipulation.py
  probe_asn: null
  probe_cc: null
  probe_ip: 127.0.0.1
  software_name: ooniprobe
  software_version: 0.0.7.1-alpha
  start_time: 1354792920.0
  test_name: HTTP Header Field Manipulation
  test_version: 0.1.3
  ...
  ---
  input: null
  report:
    agent: agent
    requests:
    - request:
        body: null
        headers:
        - - Accept-Language
          - ['en-US,en;q=0.8']
        - - Accept-Encoding
          - ['gzip,deflate,sdch']
        - - Accept
          - ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']
        - - User-Agent
          - ['Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) Gecko/20070725
              Firefox/2.0.0.6']
        - - Accept-Charset
          - ['ISO-8859-1,utf-8;q=0.7,*;q=0.3']
        - - Host
          - [cDMxQx4pPcCnNC5.com]
        method: PUT
        url: http://127.0.0.1:57001
      response:
        body: '{"headers_dict": {"Accept-Language": ["en-US,en;q=0.8"], "Accept-Encoding":
          ["gzip,deflate,sdch"], "Host": ["cDMxQx4pPcCnNC5.com"], "Accept": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          "User-Agent": ["Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6)
          Gecko/20070725 Firefox/2.0.0.6"], "Accept-Charset": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          "Connection": ["close"]}, "request_line": "PUT / HTTP/1.1", "request_headers":
          [["Connection", "close"], ["Accept-Language", "en-US,en;q=0.8"], ["Accept-Encoding",
          "gzip,deflate,sdch"], ["Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          ["User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6)
          Gecko/20070725 Firefox/2.0.0.6"], ["Accept-Charset", "ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          ["Host", "cDMxQx4pPcCnNC5.com"]]}'
        code: 200
        headers: []
    socksproxy: null
    tampering:
      header_field_name: false
      header_field_number: false
      header_field_value: false
      header_name_capitalization: false
      header_name_diff: []
      request_line_capitalization: false
      total: false
  test_name: test_put
  test_runtime: 0.023853063583374023
  test_started: 1354807320.864641
  ...
  ---
  input: null
  report:
    agent: agent
    requests:
    - request:
        body: null
        headers:
        - - aCcept-LANguage
          - ['en-US,en;q=0.8']
        - - acCEPt-ENcODING
          - ['gzip,deflate,sdch']
        - - AccEPT
          - ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']
        - - usER-AGenT
          - [Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)]
        - - aCcEpt-ChARseT
          - ['ISO-8859-1,utf-8;q=0.7,*;q=0.3']
        - - hosT
          - [Vw0mRN7DmC0IFU0.com]
        method: Get
        url: http://127.0.0.1:57001
      response:
        body: '{"headers_dict": {"aCcept-LANguage": ["en-US,en;q=0.8"], "acCEPt-ENcODING":
          ["gzip,deflate,sdch"], "hosT": ["Vw0mRN7DmC0IFU0.com"], "AccEPT": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          "usER-AGenT": ["Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR
          1.1.4322)"], "aCcEpt-ChARseT": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"], "Connection":
          ["close"]}, "request_line": "Get / HTTP/1.1", "request_headers": [["Connection",
          "close"], ["aCcept-LANguage", "en-US,en;q=0.8"], ["acCEPt-ENcODING", "gzip,deflate,sdch"],
          ["AccEPT", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          ["usER-AGenT", "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR
          1.1.4322)"], ["aCcEpt-ChARseT", "ISO-8859-1,utf-8;q=0.7,*;q=0.3"], ["hosT",
          "Vw0mRN7DmC0IFU0.com"]]}'
        code: 200
        headers: []
    socksproxy: null
    tampering:
      header_field_name: false
      header_field_number: false
      header_field_value: false
      header_name_capitalization: false
      header_name_diff: []
      request_line_capitalization: false
      total: false
  test_name: test_get_random_capitalization
  test_runtime: 0.035381078720092773
  test_started: 1354807320.866462
  ...
  ---
  input: null
  report:
    agent: agent
    requests:
    - request:
        body: null
        headers:
        - - ACcEPt-lANGuAgE
          - ['en-US,en;q=0.8']
        - - AcCePT-EnCodiNg
          - ['gzip,deflate,sdch']
        - - acCept
          - ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']
        - - USEr-Agent
          - [Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.0]
        - - AccepT-cHARsEt
          - ['ISO-8859-1,utf-8;q=0.7,*;q=0.3']
        - - HOst
          - [1numISAjBIEifu1.com]
        method: pOst
        url: http://127.0.0.1:57001
      response:
        body: '{"headers_dict": {"ACcEPt-lANGuAgE": ["en-US,en;q=0.8"], "AcCePT-EnCodiNg":
          ["gzip,deflate,sdch"], "HOst": ["1numISAjBIEifu1.com"], "acCept": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          "USEr-Agent": ["Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera
          8.0"], "AccepT-cHARsEt": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"], "Connection":
          ["close"]}, "request_line": "pOst / HTTP/1.1", "request_headers": [["Connection",
          "close"], ["ACcEPt-lANGuAgE", "en-US,en;q=0.8"], ["AcCePT-EnCodiNg", "gzip,deflate,sdch"],
          ["acCept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          ["USEr-Agent", "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera
          8.0"], ["AccepT-cHARsEt", "ISO-8859-1,utf-8;q=0.7,*;q=0.3"], ["HOst", "1numISAjBIEifu1.com"]]}'
        code: 200
        headers: []
    socksproxy: null
    tampering:
      header_field_name: false
      header_field_number: false
      header_field_value: false
      header_name_capitalization: false
      header_name_diff: []
      request_line_capitalization: false
      total: false
  test_name: test_post_random_capitalization
  test_runtime: 0.046284914016723633
  test_started: 1354807320.868329
  ...
  ---
  input: null
  report:
    agent: agent
    requests:
    - request:
        body: null
        headers:
        - - Accept-Language
          - ['en-US,en;q=0.8']
        - - Accept-Encoding
          - ['gzip,deflate,sdch']
        - - Accept
          - ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']
        - - User-Agent
          - [Opera/9.00 (Windows NT 5.1; U; en)]
        - - Accept-Charset
          - ['ISO-8859-1,utf-8;q=0.7,*;q=0.3']
        - - Host
          - [9ogjh0OCzT1arR8.com]
        method: POST
        url: http://127.0.0.1:57001
      response:
        body: '{"headers_dict": {"Accept-Language": ["en-US,en;q=0.8"], "Accept-Encoding":
          ["gzip,deflate,sdch"], "Host": ["9ogjh0OCzT1arR8.com"], "Accept": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          "User-Agent": ["Opera/9.00 (Windows NT 5.1; U; en)"], "Accept-Charset": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          "Connection": ["close"]}, "request_line": "POST / HTTP/1.1", "request_headers":
          [["Connection", "close"], ["Accept-Language", "en-US,en;q=0.8"], ["Accept-Encoding",
          "gzip,deflate,sdch"], ["Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          ["User-Agent", "Opera/9.00 (Windows NT 5.1; U; en)"], ["Accept-Charset", "ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          ["Host", "9ogjh0OCzT1arR8.com"]]}'
        code: 200
        headers: []
    socksproxy: null
    tampering:
      header_field_name: false
      header_field_number: false
      header_field_value: false
      header_name_capitalization: false
      header_name_diff: []
      request_line_capitalization: false
      total: false
  test_name: test_post
  test_runtime: 0.058208942413330078
  test_started: 1354807320.870338
  ...
  ---
  input: null
  report:
    agent: agent
    requests:
    - request:
        body: null
        headers:
        - - Accept-laNguagE
          - ['en-US,en;q=0.8']
        - - aCcEpt-EnCODIng
          - ['gzip,deflate,sdch']
        - - acCePt
          - ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']
        - - uSer-AGeNT
          - [Opera/9.00 (Windows NT 5.1; U; en)]
        - - aCcept-CHArSET
          - ['ISO-8859-1,utf-8;q=0.7,*;q=0.3']
        - - HosT
          - [Upd9yWpA0TMhUua.com]
        method: GET
        url: http://127.0.0.1:57001
      response:
        body: '{"headers_dict": {"Accept-laNguagE": ["en-US,en;q=0.8"], "aCcEpt-EnCODIng":
          ["gzip,deflate,sdch"], "HosT": ["Upd9yWpA0TMhUua.com"], "acCePt": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          "uSer-AGeNT": ["Opera/9.00 (Windows NT 5.1; U; en)"], "aCcept-CHArSET": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          "Connection": ["close"]}, "request_line": "GET / HTTP/1.1", "request_headers":
          [["Connection", "close"], ["Accept-laNguagE", "en-US,en;q=0.8"], ["aCcEpt-EnCODIng",
          "gzip,deflate,sdch"], ["acCePt", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          ["uSer-AGeNT", "Opera/9.00 (Windows NT 5.1; U; en)"], ["aCcept-CHArSET", "ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          ["HosT", "Upd9yWpA0TMhUua.com"]]}'
        code: 200
        headers: []
    socksproxy: null
    tampering:
      header_field_name: false
      header_field_number: false
      header_field_value: false
      header_name_capitalization: false
      header_name_diff: []
      request_line_capitalization: false
      total: false
  test_name: test_get
  test_runtime: 0.068952083587646484
  test_started: 1354807320.872004
  ...
  ---
  input: null
  report:
    agent: agent
    requests:
    - request:
        body: null
        headers:
        - - accEpt-lANGuAGE
          - ['en-US,en;q=0.8']
        - - acCePt-encodINg
          - ['gzip,deflate,sdch']
        - - aCCepT
          - ['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']
        - - uSer-AGent
          - [Opera/9.20 (Windows NT 6.0; U; en)]
        - - ACcepT-cHarSEt
          - ['ISO-8859-1,utf-8;q=0.7,*;q=0.3']
        - - HOsT
          - [UTqJhv92syxk0nj.com]
        method: pUt
        url: http://127.0.0.1:57001
      response:
        body: '{"headers_dict": {"accEpt-lANGuAGE": ["en-US,en;q=0.8"], "acCePt-encodINg":
          ["gzip,deflate,sdch"], "HOsT": ["UTqJhv92syxk0nj.com"], "aCCepT": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          "uSer-AGent": ["Opera/9.20 (Windows NT 6.0; U; en)"], "ACcepT-cHarSEt": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          "Connection": ["close"]}, "request_line": "pUt / HTTP/1.1", "request_headers":
          [["Connection", "close"], ["accEpt-lANGuAGE", "en-US,en;q=0.8"], ["acCePt-encodINg",
          "gzip,deflate,sdch"], ["aCCepT", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
          ["uSer-AGent", "Opera/9.20 (Windows NT 6.0; U; en)"], ["ACcepT-cHarSEt", "ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
          ["HOsT", "UTqJhv92syxk0nj.com"]]}'
        code: 200
        headers: []
    socksproxy: null
    tampering:
      header_field_name: false
      header_field_number: false
      header_field_value: false
      header_name_capitalization: false
      header_name_diff: []
      request_line_capitalization: false
      total: false
  test_name: test_put_random_capitalization
  test_runtime: 0.080827951431274414
  test_started: 1354807320.8738551
  ...


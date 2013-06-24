.. OONI documentation master file.

Welcome to the OONI developer documentation
===========================================

ooniprobe is tool for performing internet censorship measurements. Our goal is
to achieve a command data format and set of methodologies for conducting
censorship related research.

If you are a user interesting in running the ooniprobe command line tool see:

  https://github.com/hellais/ooni-probe#getting-started

The two main software components of ooniprobe are ooniprobe and oonib.

ooniprobe
*********

Is the tool that volunteers and researches interested in contributing data to
the project should be running.

ooniprobe allows the user to select what test should be run and what backend
should be used for storing the test report and/or assisting them in the running
of the test.

ooniprobe tests are divided into two categories: **Traffic Manipulation** and
**Content Blocking**.

**Traffic Manipulation** tests aim to detect the presence of some sort of
tampering with the internet traffic between the probe and a remote test helper
backend. As such they usually require the selection of a oonib backend
component for running the test.

**Content Blocking** are aimed at enumerating the kind of content that is
blocked from the probes network point of view. As such they usually require to
have specified an input list for running the test.

Core ooniprobe Tests
--------------------

The source for `Content blocking tests
<https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/data/nettests/blocking>`_
and `Traffic Manipulation tests
<https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/data/nettests/blocking>`_
can be found in the nettests/blocking and nettests/manipulation directories
respectively.

Content Blocking Tests
......................

  * `DNSConsistency <tests/dnsconsistency.html>`_

  * `HTTP Requests <tests/http_requests.html>`_

  * `TCP Connect <tests/tcpconnect.html>`_


Traffic Manipulation Tests
..........................

  * `HTTP Invalid Request Line: <tests/http_invalid_request_line.html>`_

  * `DNS Spoof <tests/dnsspoof.html>`_

  * `HTTP Header Field Manipulation <tests/http_header_field_manipulation.html>`_

  * `Traceroute <tests/traceroute.html>`_

  * `HTTP Host <tests/http_host.html>`_

Other tests
...........

We also have some other tests that are currently not fully supported or still
being experimented with.

You can find these in:

  * `data/nettests/experimental
    <https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/data/nettests/experimental>`_

Tests that don't do a measurement but are useful for scanning can be found in:

  * `data/nettests/scanning
    <https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/data/nettests/scanning>`_

Tests that involve running third party tools may be found in:

  * `data/nettests/third_party
    <https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/data/nettests/third_party>`_

oonib
*****

This is the server side component of ooniprobe. It will store that data
collected from ooniprobes and it will run a series of Test Helpers that assist
`Traffic Manipulation Tests`_ in performing their measurements.

Test Helpers
------------

The currently implemented test helpers are the following:

  * `SSL Test Helpers
    <https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/oonib/testhelpers/ssl_helpers.py>`_

  * `HTTP Test Helpers
    <https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/oonib/testhelpers/http_helpers.py>`_

  * `TCP Test Helpers
    <https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/oonib/testhelpers/tcp_helpers.py>`_

  * `DNS Test Helpers
    <https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/oonib/testhelpers/dns_helpers.py>`_

More developer documentation
****************************

.. toctree::
    :maxdepth: 2
    :glob:

    architecture
    oonib
    reports
    writing_tests
    api/*
    nettests/modules
    glossary

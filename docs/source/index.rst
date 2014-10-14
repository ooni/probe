.. OONI documentation master file.

Welcome to the OONI developer documentation
===========================================

ooniprobe is tool for performing internet censorship measurements. Our goal is
to achieve a command data format and set of methodologies for conducting
censorship related research.

If you are a user interesting in running the ooniprobe command line tool see:

    https://gitweb.torproject.org/ooni-probe.git/blob/HEAD:/README.rst

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

Threat Model
------------

Our adversary is capable of doing country wide network surveillance and 
manipulation of network traffic.

The goals of our adversary are:

  * Restrict access to certain content, while not degrading overall quality of 
    the network
  * Monitor the network in a way that they are able to identify misuse of it in
    real time

More specifc to the running of network filtering detection tests:

1. Detect actors performing censorship detection tests
2. Fool people running such tests into believing that the network is 
   unrestricted

*Note* that while 2) => 1) it is not true that 1) => 2) as the identification of 
such actors does not necessarily have to happen in real time.
While our intention is to minimize the risk of users running OONI probe to be 
identified, this comes with a tradeoff in accuracy. It is therefore necessary in 
certain tests to trade-off fingerprintability in favour of tests accuracy.

This is why we divide tests based on what risk the user running it can face, 
allowing the user to freely choose what threat model they wish to adere to.

Installation
------------

**Read this before running ooniprobe!**

Running ooniprobe is a potentially risky activity. This greatly depends on the
jurisdiction in which you are in and which test you are running. It is
technically possible for a person observing your internet connection to be
aware of the fact that you are running ooniprobe. This means that if running
network measurement tests is something considered to be illegal in your country
then you could be spotted.

Futhermore, ooniprobe takes no precautions to protect the install target machine
from forensics analysis.  If the fact that you have installed or used ooni
probe is a liability for you, please be aware of this risk.

Debian based systems
....................

`sudo sh -c 'echo "deb http://deb.ooni.nu/ooni wheezy main" >> /etc/apt/sources.list'`

`gpg --keyserver pgp.mit.edu --recv-key 0x49B8CDF4`

`gpg --export 89AB86D4788F3785FE9EDA31F9E2D9B049B8CDF4 | sudo apt-key add -`

`sudo apt-get update && sudo apt-get install ooniprobe`

Linux
.....

We believe that ooniprobe runs reasonably well on Debian GNU/Linux wheezy as
well as versions of Ubuntu such as natty and later releases. Running ooniprobe
without installing it is supported with the following commands:

`git clone https://git.torproject.org/ooni-probe.git`

`cd ooni-probe`

`./setup-dependencies.sh`

`python setup.py install`

Setting up development environment
..................................

On debian based systems this can be done with:

`Vsudo apt-get install libgeoip-dev python-virtualenv virtualenvwrapper`

`mkvirtualenv ooniprobe`

`python setup.py install`

`pip install -r requirements-dev.txt`

Other platforms (with Vagrant)
..............................

`Install Vagrant <https://www.vagrantup.com/downloads.html>`_ 
and `Install Virtualbox <https://www.virtualbox.org/wiki/Downloads>`_

**On OSX:**

If you don't have it install `homebrew <http://mxcl.github.io/homebrew/>`_

`brew install git`

**On debian/ubuntu:**

`sudo apt-get install git`

1. Open a Terminal and run:

`git clone https://git.torproject.org/ooni-probe.git`

`cd ooni-probe/`

`vagrant up`

2. Login to the box with:

`vagrant ssh`

ooniprobe will be installed in `/ooni`.

3. You can run tests with:

`ooniprobe blocking/http_requests -f /ooni/inputs/input-pack/alexa-top-1k.txt`

Using ooniprobe
---------------

**Net test** is a set of measurements to assess what kind of internet censorship is occurring.

**Decks** are collections of ooniprobe nettests with some associated inputs.

**Collector** is a service used to report the results of measurements.

**Test helper** is a service used by a probe for successfully performing its measurements.

**Bouncer** is a service used to discover the addresses of test helpers and collectors.

Configuring ooniprobe
.....................

You may edit the configuration for ooniprobe by editing the configuration file
found inside of `~/.ooni/ooniprobe.conf`.

By default ooniprobe will not include personal identifying information in the
test result, nor create a pcap file. This behavior can be personalized.

Running decks
.............

You will find all the installed decks inside of `/usr/share/ooni/decks`.

You may then run a deck by using the command line option `-i`:

As root:

`ooniprobe -i /usr/share/ooni/decks/mlab.deck`

Or as a user:

`ooniprobe -i /usr/share/ooni/decks/mlab_no_root.deck`

Or:

As root:

`ooniprobe -i /usr/share/ooni/decks/complete.deck`

Or as a user:

`ooniprobe -i /usr/share/ooni/decks/complete_no_root.deck`

The above tests will require around 20-30 minutes to complete depending on your network speed.

If you would prefer to run some faster tests you should run:
As root:

`ooniprobe -i /usr/share/ooni/decks/fast.deck`

Or as a user:

`ooniprobe -i /usr/share/ooni/decks/fast_no_root.deck`

Running net tests
.................

You may list all the installed stable net tests with:

`ooniprobe -s`

You may then run a nettest by specifying its name for example:

`ooniprobe manipulation/http_header_field_manipulation`

It is also possible to specify inputs to tests as URLs:


`ooniprobe blocking/http_requests -f httpo://ihiderha53f36lsd.onion/input/37e60e13536f6afe47a830bfb6b371b5cf65da66d7ad65137344679b24fdccd1`

You can find the result of the test in your current working directory.

By default the report result will be collected by the default ooni collector
and the addresses of test helpers will be obtained from the default bouncer.

You may also specify your own collector or bouncer with the options `-c` and
`-b`.

(Optional) Install obfsproxy
----------------------------

Install the latest version of obfsproxy for your platform.

`Download Obfsproxy <https://www.torproject.org/projects/obfsproxy.html.en>`_

Bridges and obfsproxy bridges
-----------------------------

ooniprobe submits reports to oonib report collectors through Tor to a hidden
service endpoint. By default, ooniprobe uses the installed system Tor, but can
also be configured to launch Tor (see the advanced.start_tor option in
ooniprobe.conf), and ooniprobe supports bridges (and obfsproxy bridges, if
obfsproxy is installed). The tor.bridges option in ooniprobe.conf sets the path
to a file that should contain a set of "bridge" lines (of the same format as
used in torrc, and as returned by https://bridges.torproject.org). If obfsproxy
bridges are to be used, the path to the obfsproxy binary must be configured.
See option advanced.obfsproxy_binary, in ooniprobe.conf.

Setting capabilities on your virtualenv python binary
-----------------------------------------------------

If your distributation supports capabilities you can avoid needing to run OONI as root:

`setcap cap_net_admin,cap_net_raw+eip /path/to/your/virtualenv's/python`

Core ooniprobe Tests
--------------------

The source for `Content blocking tests
<https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/ooni/nettests/blocking>`_
and `Traffic Manipulation tests
<https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/ooni/nettests/blocking>`_
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

  * `ooni/nettests/experimental
    <https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/ooni/nettests/experimental>`_

Tests that don't do a measurement but are useful for scanning can be found in:

  * `ooni/nettests/scanning
    <https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/ooni/nettests/scanning>`_

Tests that involve running third party tools may be found in:

  * `ooni/nettests/third_party
    <https://gitweb.torproject.org/ooni-probe.git/tree/HEAD:/ooni/nettests/third_party>`_

oonib
*****

This is the server side component of ooniprobe. It will store that data
collected from ooniprobes and it will run a series of Test Helpers that assist
`Traffic Manipulation Tests`_ in performing their measurements.

Test Helpers
------------

The currently implemented test helpers are the following:

  * `SSL Test Helpers
    <https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/ssl_helpers.py>`_

  * `HTTP Test Helpers
    <https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/http_helpers.py>`_

  * `TCP Test Helpers
    <https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/tcp_helpers.py>`_

  * `DNS Test Helpers
    <https://gitweb.torproject.org/oonib.git/blob/HEAD:/oonib/testhelpers/dns_helpers.py>`_

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

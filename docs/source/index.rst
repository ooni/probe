.. OONI documentation master file.

Welcome to the OONI documentation!
==================================

    The Net interprets censorship as damage and routes around it.
                John Gilmore; TIME magazine (6 December 1993)

OONI, the Open Observatory of Network Interference, is a global observation
network which aims is to collect high quality data using open methodologies,
using Free and Open Source Software (FL/OSS) to share observations and data
about the various types, methods, and amounts of network tampering in the world.


Getting started
***************

If you choose to use virtualenv to setup your development environment you will
need to do the following::

    virtualenv ENV
    source ENV/bin/activate
    pip install twisted Scapy pyyaml pyOpenSSL

To get the latest version of scapy you will need mercurial. You can then install
it with::

    pip install hg+http://hg.secdev.org/scapy

On debian you can install all the dependecies with apt-get with this command::

    apt-get install python-twisted python-twisted-names python-yaml python-scapy python-beautifulsoup

Once you have installed all the dependencies OONI tests can be run like so::

    bin/ooniprobe path/to/test.py --cmd1 foo --cmd2 bar


Contents
********

.. toctree::
    :maxdepth: 2
    :glob:

    install
    tutorial
    writing_tests
    api/*
    glossary



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

Requirements:

    * Git: http://git-scm.com/book/en/Getting-Started-Installing-Git
    * Python >= 2.6: http://www.python.org/download/releases/
    * pip: http://www.pip-installer.org/en/latest/

On debian based systems these can be installed with:

    apt-get install git-core python python-pip python-dev

The python dependencies required for running ooniprobe are:

    * Twisted
    * Scapy >= 2.2.0
    * txtorcon

They can be installed from the requirements.txt with:

    pip install -r requirements.txt

You are highly recommended to do so from inside of a virtual environment, since
pip does not download the packages via SSL and you will need to install it
system wide.

This will require you to have installed virtualenv.

    apt-get install python-virtualenv

To create a new virtual environment do

    virtualenv env

Then install OONI with:

    pip install -r requirements.txt

Contents
********

.. toctree::
    :maxdepth: 2
    :glob:

    oonib
    install
    writing_tests
    api/*
    glossary



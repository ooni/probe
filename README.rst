ooniprobe: a network interference detection tool
================================================

.. image:: https://travis-ci.org/TheTorProject/ooni-probe.png?branch=master
    :target: https://travis-ci.org/TheTorProject/ooni-probe

.. image:: https://coveralls.io/repos/TheTorProject/ooni-probe/badge.png
    :target: https://coveralls.io/r/TheTorProject/ooni-probe

.. image:: https://slack.openobservatory.org/badge.svg
    :target: https://slack.openobservatory.org/badge.svg

___________________________________________________________________________

.. image:: https://ooni.torproject.org/images/ooni-header-mascot.png
    :target: https:://ooni.torproject.org/

OONI, the Open Observatory of Network Interference, is a global observation
network which aims is to collect high quality data using open methodologies,
using Free and Open Source Software (FL/OSS) to share observations and data
about the various types, methods, and amounts of network tampering in the
world.


    "The Net interprets censorship as damage and routes around it."
                - John Gilmore; TIME magazine (6 December 1993)


ooniprobe is the first program that users run to probe their network and to
collect data for the OONI project. Are you interested in testing your network
for signs of surveillance and censorship? Do you want to collect data to share
with others, so that you and others may better understand your network? If so,
please read this document and we hope ooniprobe will help you to gather
network data that will assist you with your endeavors!

Read this before running ooniprobe!
-----------------------------------

Running ooniprobe is a potentially risky activity. This greatly depends on the
jurisdiction in which you are in and which test you are running. It is
technically possible for a person observing your internet connection to be
aware of the fact that you are running ooniprobe. This means that if running
network measurement tests is something considered to be illegal in your country
then you could be spotted.

Furthermore, ooniprobe takes no precautions to protect the install target machine
from forensics analysis.  If the fact that you have installed or used ooni
probe is a liability for you, please be aware of this risk.

OONI in 5 minutes
=================

The latest ooniprobe version for Debian and Ubuntu releases can be found in the
deb.torproject.org package repository.

On Debian stable (jessie)::

    gpg --keyserver keys.gnupg.net --recv A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89
    gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
    echo 'deb http://deb.torproject.org/torproject.org jessie main' | sudo tee /etc/apt/sources.list.d/ooniprobe.list
    sudo apt-get update
    sudo apt-get install ooniprobe deb.torproject.org-keyring

On Debian testing::

    gpg --keyserver keys.gnupg.net --recv A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89
    gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
    echo 'deb http://deb.torproject.org/torproject.org testing main' | sudo tee /etc/apt/sources.list.d/ooniprobe.list
    sudo apt-get update
    sudo apt-get install ooniprobe deb.torproject.org-keyring

On Debian unstable::

    gpg --keyserver keys.gnupg.net --recv A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89
    gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
    echo 'deb http://deb.torproject.org/torproject.org unstable main' | sudo tee /etc/apt/sources.list.d/ooniprobe.list
    sudo apt-get update
    sudo apt-get install ooniprobe deb.torproject.org-keyring

On Ubuntu 16.10 (yakkety), 16.04 (xenial) or 14.04 (trusty)::

    gpg --keyserver keys.gnupg.net --recv A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89
    gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
    echo 'deb http://deb.torproject.org/torproject.org $RELEASE main' | sudo tee /etc/apt/sources.list.d/ooniprobe.list
    sudo apt-get update
    sudo apt-get install ooniprobe deb.torproject.org-keyring

Note: You'll need to swap out ``$RELEASE`` for either ``yakkety``, ``xenial`` or
``trusty``. This will not happen automatically. You will also need to ensure
that you have the ``universe`` repository enabled. The ``universe`` repository
is enabled by default in a standard Ubuntu installation but may not be on some
minimal, or not standard, installations.

Installation
============

macOS
-----

You can install ooniprobe on macOS if you have installed homebrew (http://brew.sh/) with::

    brew install ooniprobe

Unix systems (with pip)
-----------------------

Make sure you have installed the following dependencies:

  * build-essential
  * python (>=2.7)
  * python-dev
  * pip
  * libgeoip-dev
  * libdumbnet-dev
  * libpcap-dev
  * libssl-dev
  * libffi-dev
  * tor (>=0.2.5.1 to run all the tor related tests)

Optional dependencies:

  * obfs4proxy

On debian based systems this can generally be done by running::

    sudo apt-get install -y build-essential libdumbnet-dev libpcap-dev libgeoip-dev libffi-dev python-dev python-pip tor libssl-dev obfs4proxy

Then you should be able to install ooniprobe by running::

    sudo pip install ooniprobe

or install ooniprobe as a user::

    pip install ooniprobe

Using ooniprobe
===============

**Net test** is a set of measurements to assess what kind of internet censorship is occurring.

**Decks** are collections of ooniprobe nettests with some associated inputs.

**Collector** is a service used to report the results of measurements.

**Test helper** is a service used by a probe for successfully performing its measurements.

**Bouncer** is a service used to discover the addresses of test helpers and collectors.

Configuring ooniprobe
---------------------

After successfully installing ooniprobe you should be able to access the web UI
on your host machine at <http://localhost:8842/> after running:: 
  ooniprobe -w 
or starting the daemon.

You should now be presented with the web UI setup wizard where you can read the
risks involved with running ooniprobe. Upon answering the quiz correctly you can
enable or disable ooniprobe tests, set how you can connect to the measurement's
collector and finally configure your privacy settings.

By default ooniprobe will not include personal identifying information in the
test results, nor create a pcap file. This behavior can be personalized.

Run ooniprobe as a service (systemd)
------------------------------------

Upon ooniprobe version 2.0.0 there is no need for cronjobs as ooniprobe-agent is
responsible for the tasks scheduling.

You can ensure that ooniprobe-agent is always running by installing and enabling
the systemd unit `ooniprobe.service`::

    wget https://raw.githubusercontent.com/TheTorProject/ooni-probe/master/scripts/systemd/ooniprobe.service --directory-prefix=/etc/systemd/system
    systemctl enable ooniprobe
    systemctl start ooniprobe

You should be able to see a similar output if ooniprobe (systemd) service is
active and loaded by running `systemctl status ooniprobe`::

    ● ooniprobe.service - ooniprobe.service, network interference detection tool
       Loaded: loaded (/etc/systemd/system/ooniprobe.service; enabled)
       Active: active (running) since Thu 2016-10-20 09:17:42 UTC; 16s ago
       Process: 311 ExecStart=/usr/local/bin/ooniprobe-agent start (code=exited, status=0/SUCCESS)
       Main PID: 390 (ooniprobe-agent)
       CGroup: /system.slice/ooniprobe.service
               └─390 /usr/bin/python /usr/local/bin/ooniprobe-agent start


Setting capabilities on your virtualenv python binary
=====================================================

If your distribution supports capabilities you can avoid needing to run OONI as root::


    setcap cap_net_admin,cap_net_raw+eip /path/to/your/virtualenv's/python2


Reporting bugs
==============

You can report bugs and issues you find with ooni-probe on The Tor Project issue
tracker filing them under the "Ooni" component: https://trac.torproject.org/projects/tor/newticket?component=Ooni.

You can either register an account or use the group account "cypherpunks" with
password "writecode".

Contributing
============

You can download the code for ooniprobe from the following git repository::


    git clone https://github.com/TheTorProject/ooni-probe.git


You should then submit patches for review as pull requests to this github repository:

https://github.com/TheTorProject/ooni-probe

Read this article to learn how to create a pull request on github (https://help.github.com/articles/creating-a-pull-request).

If you prefer not to use github (or don't have an account), you may also submit
patches as attachments to tickets.

Be sure to format the patch (given that you are working on a feature branch
that is different from master) with::


    git format-patch master --stdout > my_first_ooniprobe.patch


Setting up development environment
----------------------------------

On Debian based systems a development environment can be setup as follows: (prerequisites include build essentials, python-dev, and tor; for tor see https://www.torproject.org/docs/debian.html.en)::


    sudo apt-get install python-pip python-virtualenv virtualenv
    sudo apt-get install libgeoip-dev libffi-dev libdumbnet-dev libssl-dev libpcap-dev
    git clone https://github.com/TheTorProject/ooni-probe
    cd ooni-probe
    virtualenv venv

`virtualenv venv` will create a folder in the current directory which will
contain the Python executable files, and a copy of the pip library which you can
use to install other packages. To begin using the virtual environment, it needs
to be activated::


    source venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    python setup.py install

Then, you can check whether the installation went well with::

    ooniprobe -s

This will explain you the risks of running ooniprobe and make sure you have
understood them, afterwards it shows you the available tests.

To run the ooniprobe agent, instead, type::

    ooniprobe-agent run

To execute the unit tests for ooniprobe, type::

    coverage run $(which trial) ooni

Donate
-------

Send bitcoins to

.. image:: http://i.imgur.com/CIWHb5R.png
    :target: http://www.coindesk.com/information/how-can-i-buy-bitcoins/


1Ai9d4dhDBjxYVkKKf1pFXptEGfM1vxFBf

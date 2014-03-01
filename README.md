[![Build Status](https://travis-ci.org/TheTorProject/ooni-probe.png?branch=master)](https://travis-ci.org/TheTorProject/ooni-probe)
[![Coverage Status](https://coveralls.io/repos/TheTorProject/ooni-probe/badge.png)](https://coveralls.io/r/TheTorProject/ooni-probe)

![OONI](https://ooni.torproject.org/theme/img/ooni-logo.png)

"The Net interprets censorship as damage and routes around it."
                - John Gilmore; TIME magazine (6 December 1993)

OONI, the Open Observatory of Network Interference, is a global observation
network which aims is to collect high quality data using open methodologies,
using Free and Open Source Software (FL/OSS) to share observations and data
about the various types, methods, and amounts of network tampering in the
world.

ooniprobe is the first program that users run to probe their network and to
collect data for the OONI project. Are you interested in testing your network
for signs of surveillance and censorship? Do you want to collect data to share
with others, so that you and others may better understand your network? If so,
please read this document and we hope ooniprobe will help you to gather
network data that will assist you with your endeavors!

#### Read this before running ooniprobe!

Running ooniprobe is a potentially risky activity. This greatly depends on the
jurisdiction in which you are in and which test you are running. It is
technically possible for a person observing your internet connection to be
aware of the fact that you are running ooniprobe. This means that if running
network measurement tests is something considered to be illegal in your country
then you could be spotted.

Futhermore, ooniprobe takes no precautions to protect the install target machine
from forensics analysis.  If the fact that you have installed or used ooni
probe is a liability for you, please be aware of this risk.

## Installation

### Debian based systems

```
sudo sh -c 'echo "deb http://deb.ooni.nu/ooni wheezy main" >> /etc/apt/sources.list'
gpg --keyserver pgp.mit.edu --recv-key 0x49B8CDF4
gpg --export 89AB86D4788F3785FE9EDA31F9E2D9B049B8CDF4 | sudo apt-key add -
sudo apt-get update && sudo apt-get install ooniprobe
```

### Linux

We believe that ooniprobe runs reasonably well on Debian GNU/Linux wheezy as
well as versions of Ubuntu such as natty and later releases. Running ooniprobe
without installing it is supported with the following commands:

```
git clone https://git.torproject.org/ooni-probe.git
cd ooni-probe
./setup-dependencies.sh
python setup.py install
```

### Setting up development environment

On debian based systems this can be done with:
```
sudo apt-get install libgeoip-dev python-virtualenv virtualenvwrapper
mkvirtualenv ooniprobe
python setup.py install
pip install -r requirements-dev.txt
```

### Other platforms (with Vagrant)

0) [Install Vagrant](https://www.vagrantup.com/downloads.html) and [Install Virtualbox](https://www.virtualbox.org/wiki/Downloads)

0.1)

On OSX:

If you don't have it install homebrew http://mxcl.github.io/homebrew/

```
brew install git
```

On debian/ubuntu:

```
sudo apt-get install git
```

1) Open a Terminal and run:

```
git clone https://git.torproject.org/ooni-probe.git
cd ooni-probe/
vagrant up
```

2) Login to the box with:

```
vagrant ssh
```

ooniprobe will be installed in `/ooni`.

3) You can run tests with:

```
ooniprobe blocking/http_requests -f /ooni/inputs/input-pack/alexa-top-1k.txt
```

## Using ooniprobe

**Net test** is a set of measurements to assess what kind of internet censorship is occurring.

**Decks** are collections of ooniprobe nettests with some associated inputs.

**Collector** is a service used to report the results of measurements.

**Test helper** is a service used by a probe for successfully performing its measurements.

**Bouncer** is a service used to discover the addresses of test helpers and collectors.

### Configuring ooniprobe

You may edit the configuration for ooniprobe by editing the configuration file
found inside of `~/.ooni/ooniprobe.conf`.

By default ooniprobe will not include personal identifying information in the
test result, nor create a pcap file. This behavior can be personalized.

### Running decks

You will find all the installed decks inside of `/usr/share/ooni/decks`.

You may then run a deck by using the command line option `-i`:

As root:
```
ooniprobe -i /usr/share/ooni/decks/mlab.deck
```

Or as a user:
```
ooniprobe -i /usr/share/ooni/decks/mlab_no_root.deck
```

Or:

As root:
```
ooniprobe -i /usr/share/ooni/decks/complete.deck
```

Or as a user:
```
ooniprobe -i /usr/share/ooni/decks/complete_no_root.deck
```

The above tests will require around 20-30 minutes to complete depending on your network speed.

If you would prefer to run some faster tests you should run:
As root:
```
ooniprobe -i /usr/share/ooni/decks/fast.deck
```

Or as a user:
```
ooniprobe -i /usr/share/ooni/decks/fast_no_root.deck
```

### Running net tests

You may list all the installed stable net tests with:

```
ooniprobe -s
```

You may then run a nettest by specifying its name for example:

```
ooniprobe manipulation/http_header_field_manipulation
```

It is also possible to specify inputs to tests as URLs:

```
ooniprobe blocking/http_requests -f httpo://ihiderha53f36lsd.onion/input/37e60e13536f6afe47a830bfb6b371b5cf65da66d7ad65137344679b24fdccd1
```

You can find the result of the test in your current working directory.

By default the report result will be collected by the default ooni collector
and the addresses of test helpers will be obtained from the default bouncer.

You may also specify your own collector or bouncer with the options `-c` and
`-b`.

## (Optional) Install obfsproxy

Install the latest version of obfsproxy for your platform.

[Download Obfsproxy](https://www.torproject.org/projects/obfsproxy.html.en)

## Bridges and obfsproxy bridges

ooniprobe submits reports to oonib report collectors through Tor to a hidden
service endpoint. By default, ooniprobe uses the installed system Tor, but can
also be configured to launch Tor (see the advanced.start_tor option in
ooniprobe.conf), and ooniprobe supports bridges (and obfsproxy bridges, if
obfsproxy is installed). The tor.bridges option in ooniprobe.conf sets the path
to a file that should contain a set of "bridge" lines (of the same format as
used in torrc, and as returned by https://bridges.torproject.org). If obfsproxy
bridges are to be used, the path to the obfsproxy binary must be configured.
See option advanced.obfsproxy_binary, in ooniprobe.conf.

## Setting capabilities on your virtualenv python binary

If your distributation supports capabilities you can avoid needing to run OONI as root:

```
setcap cap_net_admin,cap_net_raw+eip /path/to/your/virtualenv's/python
```

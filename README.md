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

## OONI in 5 minutes

On debian:

```
sudo sh -c 'echo "deb http://deb.ooni.nu/ooni wheezy main" >> /etc/apt/sources.list'
gpg --keyserver pgp.mit.edu --recv-key 0x49B8CDF4
gpg --export 89AB86D4788F3785FE9EDA31F9E2D9B049B8CDF4 | sudo apt-key add -
sudo apt-get update && sudo apt-get install ooniprobe
```

On unix systems:
```
sudo pip install ooniprobe
```

The run:
```
mkdir my_decks
sudo ooniresource --update-inputs --update-geoip
oonideckgen -o my_decks/
```

The output from the last command will tell you how to run ooniprobe to perform
the measurment.

If you would like to contribute measurements to OONI daily you can also add
this to your crontab:

```
@daily ooni $THE_OONI_COMMAND
```

This command should automatically do it if you did not quit the shell
```
(crontab -l 2>/dev/null; echo "@daily ooni $THE_OONI_COMMAND") | crontab -
```

## Installation

### Debian based systems

```
sudo sh -c 'echo "deb http://deb.ooni.nu/ooni wheezy main" >> /etc/apt/sources.list'
gpg --keyserver pgp.mit.edu --recv-key 0x49B8CDF4
gpg --export 89AB86D4788F3785FE9EDA31F9E2D9B049B8CDF4 | sudo apt-key add -
sudo apt-get update && sudo apt-get install ooniprobe
```

### Unix systems

On other unix based systems you can install ooniprobe from pypi with:

```
sudo pip install ooniprobe
```

### With Vagrant

We also provide a vagrant file in case you don't feel like installing it on
your system.

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
ooniprobe blocking/http_requests -f /ooni/example_inputs/alexa-top-1k.txt
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

### Updating resources

To generate decks you will have to update the input resources of ooniprobe.

This can be done with:

```
ooniresource --update-inputs
```

If you get a permission error, you may have to run the command as root or
change the ooniprobe data directory inside of `ooniprobe.conf`.

On some platforms, for example debian contrib, you will not get all the geoip
related files needed. In that case it is possible to manually download them
with `ooniresources`:

```
ooniresource --update-geoip
```

### Generating decks

You can generate decks for your country thanks to the oonideckgen command.

If you wish, for example, to generate a deck to be run in the country of Italy,
you can do so (be sure to have updated the input resources first) by running:

```
oonideck --country-code IT --output ~/
```

You will now have in your home a folder called `deck-it`, containing the ooni
deck (ends with .deck) and the inputs.
Note: that you should not move the `deck-*` directory once it has been
generated as the paths to the inputs referenced by the test in the deck are
absolute. If you want your deck to live in another directory you must
regenerated it.

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


## Reporting bugs

You can report bugs and issues you find with ooni-probe on The Tor Projec issue
tracker [filing them under the "Ooni" component](https://trac.torproject.org/projects/tor/newticket?component=Ooni).

You can either register an account or use the group account "cypherpunks" with
password "writecode".

## Contributing

You can download the code for ooniprobe from the following git repository:

```
git clone https://git.torproject.org/ooni-probe.git
```

It is also viewable on the web via [https://gitweb.torproject.org/ooni-probe.git](https://git.torproject.org/ooni-probe.git).

You should then submit patches for review as pull requests to this github repository: 

https://github.com/TheTorProject/ooni-probe

Read this article to learn how to [create a pull request on github](https://help.github.com/articles/creating-a-pull-request).

If you prefer not to use github (or don't have an account), you may also submit
patches as attachments to tickets.

Be sure to format the patch (given that you are working on a feature branch that is different from master) with:

```
git format-patch master --stdout > my_first_ooniprobe.patch
```

### Setting up development environment

On debian based systems this can be done with:
```
sudo apt-get install libgeoip-dev python-virtualenv virtualenvwrapper
mkvirtualenv ooniprobe
python setup.py install
pip install -r requirements-dev.txt
```


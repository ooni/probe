ooniprobe
=========

Synopsis
--------

**ooniprobe** [*options*] ([*test name*] | [*path to nettest*.py])

Description
-----------

:program:`ooniprobe`, is a tool for performing internet censorship
measurements. Our goal is to achieve a common data format and set of
methodologies for conducting censorship related research.

Options
-------

-h, --help
    Display help and exit.

-n, --no-collector
    Disable writing to collector

-N, --no-njson
    Disable writing to disk

-g, --no-geoip
    Disable geoip lookup on start. 
    Warning: By using this option the IP address of the user executing ooniprobe is not excluded from the report.

-s, --list
    List the currently installed ooniprobe nettests

-v, --verbose
    Show more verbose information

-w, --web-ui
    Start the web UI

-z, --initialize
    Initialize ooniprobe to begin running it

-o, --reportfile PATH_TO_FILE
    Specify the report file name to write to.

-i, --testdeck PATH_TO_DECK
    Specify as input a test deck: a yaml file containing the tests to run and their arguments.

-c, --collector COLLECTOR_ADDRESS
    Specify the address of the collector for test results. In most cases a user
    will prefer to specify a bouncer over this.

-b, --bouncer BOUNCER_ADDRESS
    Specify the bouncer used to obtain the address of the collector and test helpers.

-l, --logfile PATH_TO_LOGFILE
    Write to this logs to this filename.

-O, --pcapfile PATH_TO_PCAPFILE
    Write a PCAP of the ooniprobe session to this filename.

-f, --configfile PATH_TO_CONFIG
    Specify a path to the ooniprobe configuration file.

-d, --datadir
    Specify a path to the ooniprobe data directory.

-a, --annotations key:value[,key2:value2]
    Annotate the report with a key:value[, key:value] format.

-P, --preferred-backend onion|https|cloudfront
    Set the preferred backend to use when submitting results and/or
    communicating with test helpers. Can be either onion, https or cloudfront

--version
    Display the ooniprobe version and exit.

ooniprobe
---------

Read this before running ooniprobe!
...................................
Running ooniprobe is a potentially risky activity. This greatly depends on the
jurisdiction in which you are in and which test you are running. It is
technically possible for a person observing your internet connection to be
aware of the fact that you are running ooniprobe. This means that if running
network measurement tests is something considered to be illegal in your country
then you could be spotted.

Furthermore, ooniprobe takes no precautions to protect the install target machine
from forensics analysis.  If the fact that you have installed or used ooni
probe is a liability for you, please be aware of this risk.

What is this?
.............

ooniprobe is the command line tool that volunteers and researches interested in
contributing data to the project should be running.

If you are interested in using ooniprobe from a graphical user interface
refer to :program:`ooniprobe-agent` and see how to run that.

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

Examples
--------

Run the web_connectivity test on http://torproject.org:

        :program:`ooniprobe web_connectivity --url http://torproject.org/`

Run the http_invalid_request_line test to detect middleboxes:

        :program:`ooniprobe http_invalid_request_line`

Run the http_header_field_manipulation test to detect middleboxes:

        :program:`ooniprobe http_header_field_manipulation`

List all the available tests:

        :program:`ooniprobe -s`

Start the web user interface:

        :program:`ooniprobe -w`

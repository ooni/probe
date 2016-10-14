Changelog
=========

v2.0.0 (Fri, 14 Oct 2016)
------------------------------
codename: mezzanine

Stable release of ooniprobe 2.0.0

Feature list:

* System daemon for running tests periodically (https://github.com/TheTorProject/ooni-probe/issues/576)

* Web user interface for viewing measurement results (https://github.com/TheTorProject/ooni-probe/issues/575)

* New deck format (https://github.com/TheTorProject/ooni-probe/issues/571)

* Local reports are written in JSON (https://github.com/TheTorProject/ooni-probe/issues/557)

* Include decks for testing reachability of Tor, websites of IM apps

* Include the platform as an annotation inside of reports

Bugfixing since previous release candidates:

* Fix -w option of ooniprobe (https://github.com/TheTorProject/ooni-probe/issues/623)

* Scheduler lockfile for RunDecks not being released (https://github.com/TheTorProject/ooni-probe/issues/612)

* Missing country testing list (https://github.com/TheTorProject/ooni-probe/issues/606)

v2.0.0-rc.3 (Mon, 19 Sep 2016)
------------------------------

Bugfixing and code cleanup

v2.0.0-rc.2 (Tue, 13 Sep 2016)
------------------------------

This is a release candidate for a major ooniprobe release.

It includes a new web user interface and a system daemon for running ooniprobe
tests.

Feature list:

* System daemon for running tests periodically (https://github.com/TheTorProject/ooni-probe/issues/576)

* Web user interface for viewing measurement results (https://github.com/TheTorProject/ooni-probe/issues/575)

* New deck format (https://github.com/TheTorProject/ooni-probe/issues/571)

* Local reports are written in JSON (https://github.com/TheTorProject/ooni-probe/issues/557)

v1.6.1 (Tue, 26 Jul 2016)
-------------------------

* Fix #569

* Fix #573

v1.6.0 (Sun, 10 Jul 2016)
-------------------------
codename: Shells and Seaweed

* Add support for cloudfrontend and HTTPS collector
https://github.com/TheTorProject/ooni-probe/issues/530

* Add bisection logic to inputProcessor (big thanks to @seamustuohy for the
  patch):
  https://github.com/TheTorProject/ooni-probe/issues/503

* Add bridge failover support:
  https://github.com/TheTorProject/ooni-probe/issues/538

* Make it possible to run tests without specifying the test type
  https://github.com/TheTorProject/ooni-probe/issues/483

Bug fixes:

* Silently ignores '--pcapfile' flag (thanks to @willscott for the patch!):
  https://github.com/TheTorProject/ooni-probe/issues/521

* The options specified on the command line should have priority over the deck
  options.
  https://github.com/TheTorProject/ooni-probe/issues/529

v1.5.1 (Fri, 3 Jun 2016)
-------------------------
codename: The Big Wave

* Add --default-collector option to oonireport

* Fix critical bug in web_connectivity test

v1.5.0 (Mon, 30 May 2016)
-------------------------
codename: The Big Wave

* Implement web_connectivity test that measures for both DNS and HTTP
  censorship.

* Fix a regression bug that lead to Tor exit ip address not being included in
  reports.

v1.4.2 (Fri, 29 Apr 2016)
-------------------------

* Hotfix for bug in serialising binary response bodies

* Use the most recent scapy version


v1.4.1 (Wed, 27 Apr 2016)
-------------------------

* Fix problem with uploading of release


v1.4.0 (Wed, 27 Apr 2016)
-------------------------

codename: Under the Sea

* Support for reporting using JSON

* Support for running ooniprobe with a message queue providing URLs to test

* Psiphon censorship circumvention test

* OpenVPN censorship circumvention test

* Add test for vanilla Tor

* Support for disabling reporting to disk

* Improvements to HTTP response body decoding (includes fix that lead to empty
  bodies being misrepresented)

* Attempt to scrub the probe IP address from the body of HTTP responses


v1.3.2 (Fri, 20 Nov 2015)
-------------------------

* Implement third party test template

* Add tutorial for using TCP test

* Add tests for censorship resistance

  * Add meek test

  * Add lantern test

* Support for Twisted 15.0

* Various stability and bug fixes

v1.3.1 (Fri, 3 Apr 2015)
------------------------

* Fix bug with --help of oonireport

* Read the home directory from an environement variable

* Expose the inputs_dir and decks_dir from the config file

* Fix bug that leads to some incomplete reports not showing up with oonireport

v1.3.0 (Fri, 27 Mar 2015)
-------------------------

* Add obfs4 bridge reachability support

* Avoid hacking sys.path in bin/* scripts to support running ooniprobe from
  non-root.

* Point to the new citizenlab test lists directory

* Add support for report_id inside of reports

* Add the list of test helper addresses to the report

* Handle also unhandled exceptions inside of ooni(deckgen|report|resources)

v1.2.3-rc1 (Wed, 4 Feb 2015)
----------------------------
* Restructure directories where ooni software writes/reads from
  https://trac.torproject.org/projects/tor/ticket/14086

* Properly set exit codes of oonideckgen

* Exit cleanly if we can't find the probes IP address

* Make the DNS Consistency test handle errors better

v1.2.2 (Fri, 17 Oct 2014)
-------------------------

Who said friday 17th is only bad luck?

* Add two new report entry keys test_start_time and test_runtime

* Fix bug that lead to ooniresources not working properly

v1.2.0 (Wed, 1 Oct 2014)
-------------------------

* Introduce a new tool for generating ooniprobe test decks called oonideckgen.

* Introduce a new tool for updating resources used for geoip lookup and deck
  generation.

* Add support for policy aware bouncing in the client.
  https://trac.torproject.org/projects/tor/ticket/12579

* Various improvements to the bridge_reachability test (enable better tor
  logging and also log obfsproxy)

* Fix backward compatibility with twisted 13.1 and add regression tests for
  this.
  https://trac.torproject.org/projects/tor/ticket/13139

v1.1.1 (Sun, 24 Aug 2014)
-------------------------

* Update MANIFEST.in to include the manpages for ooniprobe and oonireport.

* Raise a more specific exception when multiple test cases are in a single
  nettest file and the usageOptions are incoherent.

v1.1.0 (Tue, 19 Aug 2014)
-------------------------

In this new release of ooniprobe we have added a new command line tool for
listing the reports that have not been published to a collector and that allows
the probe operator to choose which ones they would like to upload.

We have also made some privacy improvements to the reports (we will sanitize
all things that may look like file paths) and added metadata associated with
the maxmind database being used by the probe operator.

Here is a more detailed list of what has been done:

* Annotate on disk which reports we have submitted and which ones we have not:
  https://trac.torproject.org/projects/tor/ticket/11860

* Add tool called oonireport for publishing unpublished ooniprobe reports to a
  collector: https://trac.torproject.org/projects/tor/ticket/11862

* Probe Report does not leak filepaths anymore:
  https://trac.torproject.org/projects/tor/ticket/12706

* Reports now include version information about the maxmind database being
  used: https://trac.torproject.org/projects/tor/ticket/12771

* We now do integrity checks on the ooniprobe.conf file so that we don't start
  the tool if the config file is missing some settings or is not consistent:
  https://trac.torproject.org/projects/tor/ticket/11983
  (thanks to Alejandro López (kudrom))

* Improvements have been made to the sniffer subsystem (thanks to Alejandro
  López (kudrom))

* Fix the multi protocol traceroute test.
  https://trac.torproject.org/projects/tor/ticket/12883

Minor bug fixes:

* Fix dns_spoof test (by kudrom)
  https://trac.torproject.org/projects/tor/ticket/12486

* ooni might not look at requiresTor:
  https://trac.torproject.org/projects/tor/ticket/11858

* ooni spits out gobs of tracebacks if Tor is not running and the OONI config
  says it will be:
  https://trac.torproject.org/projects/tor/ticket/11859

* The README for ooni-probe should mention the bugtracker and repository
  https://trac.torproject.org/projects/tor/ticket/11980

v1.0.2 (Fri, 9 May 2014)
------------------------

* Add ooniprobe manpage.

* Fix various security issues raised by the least authority audit.

* Add a test that checks for Tor bridge reachability.

* Record the IP address of the exit node being used in torified requests.

* Captive portal test now uses the ooni-probe test templates.

* Have better test naming consistency.

v1.0.1 (Fri, 14 Mar 2014)
-------------------------

* Fix bugs in the traceroute test that lead to not all packets being collected.

* All values inside of http_requests test are now initialized inside of setUp.

* Fix a bug that lead to the input value of the report not being set in some
  circumstances.

* Add bridge_reachability test

v1.0.0 (Thu, 20 Feb 2014)
-------------------------

* Add bouncer support for discovering test helpers and collectors

* Fix bug that lead to HTTP tests to stall

* Add support for connect_error and connection_lost_error error types

* Add support for additional Tor configuration keys

* Add disclaimer when running ooniprobe

v0.1.0 (Mon, 17 Jun 2013)
-------------------------

Improvements to HTML/JS based user interface:

  * XSRF protection

  * user supplied input specification

Bugfixing and improvements to scheduler.

v0.0.12 (Sat, 8 Jun 2013)
-------------------------

Implement JS/HTML based user interface.

Supports:

  * Starting and stopping of tests

  * Monitoring of test progress

v0.0.11 (Thu, 11 Apr 2013)
--------------------------

* Parametrize task timeout and retry count

* Set the default collector via the command line option

* Add option to disable the default collector

* Add continuous integration with travis

v0.0.10 (Wed, 26 Dec 2012)
--------------------------

ooniprobe:

* Fix bug that made HTTP based tests stall

* Update DNS Test example to not import the DNS Test template If you import the
	DNS Test template it will be considered a valid test case and command line
	argument parsing will not work as expected. see:
	#7795 for more details

* Fix major bug in DNS test template that prevented PTR lookups from working
	properly I was calling the queryUDP function with the arguments in the wrong
	order. Twisted, why you API no consistent?

* Add support for specifying the level of parallelism in tests (aka router
	melt mode)

* Do not swallow failures when a test instance fails to run fixes #7714

scripts:

* Add report archival script

Fix bug in TCP connect test that made it not properly log errors

* Refactor failure handling code in nettest Add function that traps all the
	supported failure and outputs the failure string representing it.

documentation:

* Add birdseye view of the ooniprobe architecture

* Add details on the current implementation status of ooni*

* Add draft ooniprobe API specification

* Add instructions for supervisord configuration and clean up README.md

0.0.9 (Tue, 11 Dec 2012)
------------------------

ooniprobe:

* Set the default ASN to 0

* Make Beautiful soup a soft depedency

* Add support for sending the ASN number of the probe:
	the ASN number will get sent when creating a new report

* Add support for obtaining the probes IP address via getinfo address as per
	https://trac.torproject.org/projects/tor/ticket/7447

* Fix bug in ooniprobe test decks
	https://trac.torproject.org/projects/tor/ticket/7664

oonib:

* Use twisted fdesc when writing to files

* Add support for processing the ASN number of the probe

* Test reports shall follow the specification detailed inside of docs/reports.rst

* Add support for setting the tor binary path in oonib/config.py

scripts:

* Add a very simple example on how to securely parse the ooniprobe reports

documentation:

* Add documentation for the DNSSpoof test

* Add documentation for HTTPHeaderFieldManipulation

* Clean up writing_tests.rst

* Properly use the power of sphinx!

Tests:

* fixup Netalyzr third party plugin

v0.0.8-alpha (Sun, 2 Dec 2012)
------------------------------

ooniprobe:

* Allow test resolver file to have comments.

* Autostart Tor in default configuration.

* Add support for starting Tor via txtorcon.

* Make the sniffer not run in a separate thread, but use a non blocking fdesc.
	Do some refactoring of scapy testing, following Factory creational pattern
	and a pub-sub pattern for the readers and writers.

* Extend TrueHeaders to support calculation of difference between two HTTP headers respectful of
	capitalization

* Implement test deck system for automating the specification of command line
	arguments for tests

* Implement sr1 in txscapy

* Include socksproxy address in HTTP based tests

* Include the resolver IP:Port in the report

* Changes to the report format of HTTP Test template derived tests:
	Requests are now stored inside of an array to allow
	the storing of multiple request/response pairs.

* Fix bug that lead to httpt based reports to not have the url attribute set
	properly.

* twisted Headers() class edited to avoid header fix in reference to:
	https://trac.torproject.org/projects/tor/ticket/7432

* Parametrize tor socksport for usage with modified HTTP Agent

* Update URL List test to take as input also a single URL

* Clean up filenames of reports generated by ooni-probe:
	they now follow the format $testName_report_$timestamp.yamloo

* Add ooniprobe prefix to logs

* Respect the includeip = false option in ooniprobe.conf for scapyt derivate
	tests:
	If the option to not include the IP address of the probe is set,
	change the source and destination ip address of the sent and received
	packets to 127.0.0.1.

tests:

* Implement basic keyword filtering detection test.

* Add ICMP support to multi protocol traceroute test

* parametrize max_ttl and timeout

* make max_ttl and timeout be included in the report

* Port UK Mobile Network test to new API

* Port daphn3 test

* Randomize source port by default in traceroute test and include source port in
	report

* Test and Implement HTTP Header Field Manipulation Test (rename it to what we
	had originally called it since it made most sense)

* Implement test that detects DNS spoofing

* Implement TCP payload sending test template:
	Example test based on this test template

* Make report IDs include the timestamp of the report

* Add test that detects censorship in HTTP pages based on HTTP body length

* Add socks proxy support to HTTP Test

* Create DNS Test template:
	Use such template for DNS Tamper test.
	Add example usage of DNS Test Template.

* Refactor captive portal test to run tests in threads

oonib:

* Implement basic collector for ooniprobe reports.
	Reports can be submitted over the network via http to a remote collector.
	Implement the backend component of the collector that writes submitted
	reports to flat files, following the report_id naming convention.

* Implement very simple HTTP Request backend that does only the part of HTTP we
	need for testing

* Make oonib a daemon

* Loosen up the oonib regexp to support the timestamp report format

* Add Tor Hidden Service support

* Make the reporting directory of the collector configurable

* Implement TCP Echo test helper.

scripts:

* Add fabfile for automatic deployment of ooni-probe to remote sites

documentation:

* Update documentation on how to setup ooniprobe.

v0.0.7.1-alpha (Sun, 11 Nov 2012)
---------------------------------

* Add software version to the report

* Implement basic oonib reporting to flat files containing the report ID.

* Improve HTTP Host test to work with the HTTP Requests test backend

v0.0.7-alpha (Sat, 10 Nov 2012)
-------------------------------

* Add test_name key to ooniprobe reports

* Port TCP connect test to the new API

v0.0.4-alpha (Sat, 10 Nov 2012)
-------------------------------

* Add multi protocol multi port traceroute for UDP and TCP

* Implement basic HTTP request test that does capitalization variations on the
  HTTP method.

* Bugfixing and refactoring of txscapy for sending and receiving of scapy
  packets.

v0.0.3-alpha (Fri, 9 Nov 2012)
------------------------------

* Implement logging to PCAP file support

* Remove dependency on trial

* Port china trigger to new API

* Rename keyword filtering test to HTTP keyword filtering

* Refactor install documentation.

* Convert header of ooniprobe script to a non docstring

* Add Makefile to fetch Maxmind geoip database files

* Implement GeoIP lookup support

* From configuration options it is possible to choice what level of privacy
	the prober is willing to accept. Implement config file support You are able
	to specify basic and advanced options in YAML format

* Remove raw inputs and move them to a separate repository and add Makefile to
	fetch such lists

0.0.1-alpha (Tue, 6 Nov 2012)
-----------------------------

First release of ooni-probe. woot!

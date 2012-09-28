= ooniprobe Bridget Plugin =

== Who's that? ==

Bridget is an OONI plugin for testing the reachability of bridges and relays
in the Tor network.

== Dependencies == 

In addition to the regular OONI dependencies, bridget requires
[https://github.com/meejah/txtorcon.git txtorcon]. If you don't already have
it installed on your system, there is a Makefile in ooni/lib/ which will git
clone it for you, and copy the API portions to ooni/lib/ and discard the
rest. If you're seeing errors saying "Bridget requires txtorcon!" or "Unable
to import libraries from txtorcon!", then you should use the Makefile by
doing:

    $ cd ooni/lib/ && make txtorcon

== Using Bridget ==

=== Defaults ===

'''Tor Binary Path'''
By default, Bridget will start a new Tor process from the binary at 
/usr/sbin/tor. If you have a different Tor binary that you'd like to use,
you can tell Bridget where it is by using the '--torpath' option.

'''Tor SocksPort and ControlPort'''
Also, Bridget is configured to start Tor with ControlPort=9052 and
SocksPort=9049. If you're running a firewall, you should make sure that
localhost is allowed incoming access to those ports. To use different ports,
see the '--socks' and '--control' options.

If you're a true Entropist, you can use the '--random' option to randomize
which ports are used for the SocksPort and ControlPort.

=== Running Tests === 

You'll need some assets first. 

OONI assets are simple text files describing what it is that you want
tested. Normally, one thing-to-be-tested per line, sometimes with comma
separated values. The test you're using should tell you what it wants (if it
doesn't, you should complain to one of the OONI developers). Normally, assets
look like this:

    [file:assets/things.txt]
    torproject.org
    ooni.nu
    eff.org
    riseup.net
    [...]

==== Testing Relays with Bridget ==== 

This doesn't work all the way yet. Eventually, you'll need to give bridget
an asset with one relay IP address per line, like this:

    [file:assets/relays.txt]
    123.123.123.123
    11.22.33.44
    111.1.111.1
    [...]

and you'll use it by doing:

    path-to-ooni-probe/ooni/$ ./ooniprobe.py bridget -f assets/relays.txt

Once the relays feature is functional, it will be possible to test bridges and
relays at the same time: Bridget will try to connect to a bridge, and, if that
worked, it will try to build a circuit from the provided relays, noting which
bridges/relays fail and which ones succeed. This will continue until all the
bridges and relays have been tested.

==== Testing Bridges with Bridget ==== 

Bridget will need an asset file with bridge IPs and ORPorts, one per
line. Your asset file should look like this:

    [file:assets/bridges.txt]
    11.22.33.44:443
    2.3.5.7:9001
    222.111.0.111:443
    [...]

and you'll call Bridget like this:

    path-to-ooni-probe/ooni/$ ./ooniprobe.py bridget -b assets/bridges.txt
    
==== Testing Bridge Pluggable Transports ====

Bridget can test whether a bridge with a pluggable transport, like obfsproxy,
is reachable. To reach these bridges, you need to have the pluggable transport
that you want to test installed. You should look at the documentation for that
transport to figure out how to do that.

To test a pluggable transport, do this (the quotemarks are important):

    $ ./ooniprobe.py bridget -t "/path/to/PT/binary [options]" \
          -b assets/bridges.txt


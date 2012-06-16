#!/bin/bash
SUITE="`lsb_release -c|cut -f2`";
apt-get -y install tcptraceroute traceroute iputils-ping wget dnsutils \
        python-openssl rsync openssl libevent-1.4-2 zlib1g openssh-server

# Lets make sure we can run these programs without ever becoming root again
chmod 4755 `which tcptraceroute`
chmod 4755 `which traceroute`

# Install Tor from the Tor repo here...
#cp /etc/apt/sources.list /etc/apt/sources.list.bkp
#cat << "EOF" >> /etc/apt/sources.list
#deb     http://deb.torproject.org/torproject.org $SOURCE main
#deb     http://deb.torproject.org/torproject.org experimental-$SOURCE main
#EOF
#
#gpg --keyserver keys.gnupg.net --recv 886DDD89
#gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
#apt-get update
#apt-get install tor tor-geoipdb

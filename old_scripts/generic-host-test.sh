#!/bin/bash -x
#
# A quick hack to (tcp)traceroute to a list of hosts
#

echo "tcp/conntest v0.8"
date -R
echo
/sbin/ifconfig -a
echo
/sbin/route -n
echo

ip=$1

echo "Requesting DNS results for $ip"
host -t any $ip

echo "Attempting connections with $ip..."
    echo "Testing $ip"
    tcptraceroute -m 6 -w 1 -p 80 $ip
    tcptraceroute -m 6 -w 1 -p 0 $ip
    tcptraceroute -m 6 -w 1 -p 123 $ip
    tcptraceroute -m 6 -w 1 -p 443 $ip

echo "Various traceroute attempts"
    traceroute -A $ip
    traceroute -A -I $ip
    traceroute -A -U -p 53 $ip

wget -q -O- https://check.torproject.org|grep "IP address"
echo
date -R

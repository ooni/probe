#!/bin/bash
#
# A quick hack to (tcp)traceroute to a list of hosts
#

echo "tcp/conntest v0.6"
date -R
echo
/sbin/ifconfig -a
echo
/sbin/route -n
echo

echo "Testing Twitter IP addresses..."
for ip in `cat twitter-ip-list.txt|grep 1`
do
    echo "Testing $ip"
    tcptraceroute -m 6 -w 1 $ip 80
    tcptraceroute -m 6 -w 1 $ip 0
    tcptraceroute -m 6 -w 1 $ip 123
    tcptraceroute -m 6 -w 1 $ip 443
done
echo "Various traceroute attempts"
for ip in `cat twitter-ip-list.txt|grep 1`
do
    traceroute -A $ip
    traceroute -A -I $ip
    traceroute -A -U $ip
done

wget -q -O- https://check.torproject.org|grep "IP address"
echo
date -R

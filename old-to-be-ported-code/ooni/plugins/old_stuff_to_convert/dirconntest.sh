#!/bin/bash
#
# A quick hack to (tcp)traceroute to all of the Tor Dir auths
#

echo "dirconntest v3.14"
date -R
echo
/sbin/ifconfig -a
echo
/sbin/route -n
echo

echo "Testing Tor directory auths..."
for hostinfo in "128.31.0.39 9131" "128.31.0.39 9101" \
               "86.59.21.38 80" "86.59.21.38 443" \
               "194.109.206.212 80" "194.109.206.212 443" \
               "82.94.251.203 80" "82.94.251.203 443" \
               "216.224.124.114 9030" "216.224.124.114 9090" \
               "212.112.245.170 80" "212.112.245.170 443" \
               "193.23.244.244 80" "193.23.244.244 443" \
               "208.83.223.34 443" "208.83.223.34 80" \
               "213.115.239.118 443" "213.115.239.118 80"

do
    dirauth_ip=`echo $hostinfo|cut -f1 -d\ `;
    dirauth_port=`echo $hostinfo|cut -f2 -d\ `;
    echo "Testing $dirauth_ip at `date -R`"
    tcptraceroute $dirauth_ip $dirauth_port
    echo "Various traceroute attempts"
    traceroute -A --mtu --back $dirauth_ip
    traceroute -A -I $dirauth_ip
    traceroute -A -T $dirauth_ip
    traceroute -A -U $dirauth_ip
    echo
    tcptraceroute $dirauth_ip 80
    tcptraceroute $dirauth_ip 123
    tcptraceroute $dirauth_ip 443
    tcptraceroute $dirauth_ip 0
done

date -R
host www.torproject.org
date -R
host torproject.org
date -R
host check.torproject.org

date -R
wget -q -O- https://check.torproject.org|grep "IP address"
echo
date -R

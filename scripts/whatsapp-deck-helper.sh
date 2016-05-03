#!/bin/bash
set -e

# This script grabs the CIDR IP list that Whatsapp uses to connect. Extracts
# the IPv4 addresses and convert the CIDR notations to IPs. Finally splits the
# IPs in separate list files per Whatsapp host port (IP:PORT) required for the
# http_hosts ooni-probe test.
# Required tools: prips, torsocks (optional but handy if you are blocked)

# Official Whatsapp CIDR URL
WHATSAPP_CIDR_URL="https://www.whatsapp.com/cidr.txt"
# Known Whatsapp ports
WHATSAPP_PORTS="80 443 5222 5223 5228 5060 5060 8080"
# Known Whatsapp web URLs
WHATSAPP_URLS="
www.whatsapp.com
web.whatsapp.com
www.whatsapp.com/cidr.txt
whatsapp.com
sro.whatsapp.net/client/iphone/iq.php
sro.whatsapp.net/client/android/iq.php
static.reverse.softlayer.com
"
# Whatsapp URL list file
URL_LIST="whatsappurl.list"

if [ ! -f ${URL_LIST} ]; then
	for u in ${WHATSAPP_URLS}; do
		echo -e "http://${u}\nhttps://${u}" >> ${URL_LIST}
	done
fi

# Check if prips and torsocks exists
command -V prips torsocks

torsocks wget -N ${WHATSAPP_CIDR_URL}
sed '/^.*:.*$/d' cidr.txt > cidr-ipv4.txt

# Remove /32 CIDR blocks to resolve a but in prips version <1
sed -i -e '/\/32/w whatsapp-ipv4.list' -e '//d' cidr-ipv4.txt
sed -i 's/\/32//g' whatsapp-ipv4.list

while read l; do
	prips $l; done <cidr-ipv4.txt >> whatsapp-ipv4.list

sed -i s/^.*m//g whatsapp-ipv4.list

for p in ${WHATSAPP_PORTS}; do
	sed s/$/:${p}/g whatsapp-ipv4.list > whatsapp-ipv4-${p}.list
done

# Hack make this a big fat IP:PORT list bug refernce:
# https://github.com/TheTorProject/ooni-probe/issues/493
awk '1' whatsapp-ipv4-[0-9]* > whatsapp-ipv4-ports.list

# Generate a random IP:PORTS list for the fast deck
shuf -n 500 whatsapp-ipv4-ports.list > whatsapp-ipv4-random-ports.list

#!/bin/bash
#
# Ghetto way to hack up a list of IP addresses out of the XFF list 
#
numoflines="`lynx --dump trusted-xff.html 2>&1 |wc -l`"
headcount=$(expr ${numoflines} - 11) # this might change - not a stable API
tailcount=$(expr ${numoflines} - 7) # this might change - not a stable API
numberofips=$(expr ${numoflines} - ${headcount} - ${tailcount})

#lynx --dump trusted-xff.html 2>&1 |tail -n ${tailcount}|head -n ${headcount} |cut -d\  -f 4|xargs -n 1 geoiplookup |cut -d, -f1|cut -d\  -f 4
lynx --dump trusted-xff.html 2>&1 |tail -n ${tailcount}|head -n ${headcount} |cut -d\  -f 4 > ips.txt

for ip in `cat ips.txt`;
do
echo `geoiplookup $ip|cut -d, -f1|cut -d\  -f 4`":$ip" >> ip-cc.txt; 
done

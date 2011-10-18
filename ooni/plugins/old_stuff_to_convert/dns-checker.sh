#!/bin/bash

for host in `cat twitter-host-list.txt`
do
echo "Trying to resolve: $host"
host -t any $host
done

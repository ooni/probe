#!/bin/bash

DATE="`date -u`";
cd ~/.probe/logs/;
~/.probe/bin/marco.py ~/.probe/logs/cached-consensus 2>&1 >> ~/.probe/logs/run-tests-marco-"$DATE".log;
~/.probe/bin/dirconntest.sh 2>&1 >> ~/.probe/logs/run-tests-dirconntest-"$DATE".log;

for host in `cat ~/.probe/logs/hosts.txt`;
do
  ~/.probe/bin/generic-host-test.sh $host > 2>&1 >> ~/.probe/logs/generic-host-test-"$DATE".log;
done;

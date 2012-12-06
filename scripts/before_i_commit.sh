#!/bin/sh
# This script should be run before you commit to verify that the basic tests
# are working as they should
# Once you have run it you can inspect the log file via
#
# $ less before_i_commit.log
# To clean up everything that is left by the running of this tool, do as
# following:
#
# rm *.yamloo; rm before_i_commit.log
#

rm before_i_commit.log

find . -type f -name "*.py[co]" -delete

./bin/ooniprobe -i decks/before_i_commit.testdeck

echo "Below you should not see anything"
echo "---------------------------------"
grep "Error: " before_i_commit.log
echo "---------------------------------"
echo "If you do, it means something is wrong."
echo "Read through the log file and fix it."
echo "If you are having some problems fixing some things that have to do with"
echo "the core of OONI, let's first discuss it on IRC, or open a ticket"
read
cat *yamloo | less
rm -f *yamloo

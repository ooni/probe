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

if [ -f before_i_commit.log ];
then
  # this is technically the date it was moved, not the date it was created
  mv before_i_commit.log before_i_commit-`date +%s`.log;
  touch before_i_commit.log;
else
  touch before_i_commit.log;
fi

find . -type f -name "*.py[co]" -delete

if [ -f env/bin/activate ];
then
  source env/bin/activate;
else
  echo "Assuming that your virtual environment is pre-configured...";
fi

./bin/ooniprobe -i decks/before_i_commit.testdeck

echo "Below you should not see anything"
echo "---------------------------------"
[ -f before_i_commit.log ] && grep "Error: " before_i_commit.log
echo "---------------------------------"
echo "If you do, it means something is wrong."
echo "Read through the log file and fix it."
echo "If you are having some problems fixing some things that have to do with"
echo "the core of OONI, let's first discuss it on IRC, or open a ticket"
read
cat *yamloo | less
rm -f *yamloo

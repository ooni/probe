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

./bin/ooniprobe -l before_i_commit.log -o url_lists.yamloo nettests/core/url_list.py -f test_inputs/url_lists_file.txt

./bin/ooniprobe -l before_i_commit.log -o dns_tamper_test.yamloo nettests/core/dnstamper.py -t test_inputs/dns_tamper_test_resolvers.txt -f test_inputs/dns_tamper_file.txt

#./bin/ooniprobe -l before_i_commit.log -o captive_portal_test.yamloo nettests/core/captiveportal.py

./bin/ooniprobe -l before_i_commit.log -o http_host.yamloo nettests/core/http_host.py -b http://ooni.nu/test -f test_inputs/http_host_file.txt

./bin/ooniprobe -l before_i_commit.log -o http_keyword_filtering.yamloo nettests/core/http_keyword_filtering.py -b http://ooni.nu/test/ -f test_inputs/http_keyword_filtering_file.txt

./bin/ooniprobe -l before_i_commit.log -o url_lists.yamloo nettests/core/url_list.py -f test_inputs/url_lists_file.txt

echo "Below you should not see anything"
echo "---------------------------------"
grep "Error: " before_i_commit.log
echo "---------------------------------"
echo "If you do, it means something is wrong."
echo "Read through the log file and fix it."
echo "If you are having some problems fixing some things that have to do with"
echo "the core of OONI, let's first discuss it on IRC, or open a ticket"

rm -f *yamloo

# This is an example of how to parse ooniprobe reports

from pprint import pprint
import yaml
import sys
print "Opening %s" % sys.argv[1]
f = open(sys.argv[1])
yamloo = yaml.safe_load_all(f)

report_header = yamloo.next()
print "ASN: %s" % report_header['probe_asn']
print "CC: %s" % report_header['probe_cc']
print "IP: %s" % report_header['probe_ip']
print "Start Time: %s" % report_header['start_time']
print "Test name: %s" % report_header['test_name']
print "Test version: %s" % report_header['test_version']

for report_entry in yamloo:
    pprint(report_entry)

f.close()

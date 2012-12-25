#!/usr/bin/env python
import yaml
import sys
import glob
import fcntl
import os
import re
from ipaddr import IPAddress
from datetime import timedelta
from datetime import datetime
from ooni.otime import fromTimestamp, timestamp
from ooni.otime import InvalidTimestampFormat, utcDateNow
from ooni.utils import log

###############################################################################
# You can set some config options here                                        #
###############################################################################
report_age = 1 # hours
report_archive_dir = '/home/user/oonib/reports/archived'
report_source_dir = '/home/user/oonib/reports'
valid_test_versions = ['0.1', '0.1.1', '0.4', '0.1.3']
default_probe_cc = '??'
target_permission = 0444
path_permission = 0755
retry_attempts = 100
###############################################################################

now = utcDateNow()
delta = timedelta(hours=report_age)

def filter_reports_by_age(report):
    try:
        ts,__,__ = os.path.basename(report).split('_')
        if now - fromTimestamp(ts) > delta:
            return True
    except (InvalidTimestampFormat, ValueError):
        return False

def validate_fields(fields):
    log.debug("Report fields are: %s" % fields)

    # check report version
    if fields['test_version'] not in valid_test_versions:
        log.err("Report submitted with invalid report version!")
        return False

    # check report CC
    #XXX: confirm what value we use for default CC and whether
    # or not we should support > 2 character CC
    if fields['probe_cc'] is None:
        fields['probe_cc'] = default_probe_cc
    if not re.match('[A-Z\?]{2,4}', fields['probe_cc'].upper()):
        log.err("Report submitted with invalid CC!")
        return False

    # check report ASN
    if fields['probe_asn'] is None:
        fields['probe_asn'] = 'AS0'
    if not re.match('^AS[0-9]{1,10}', fields['probe_asn'].upper()):
        log.err("Report submitted with invalid AS Number!")
        return False

    # check report timestamp
    try:
        datetime_ts = datetime.fromtimestamp(fields['start_time'])
        datetime_str = timestamp(datetime_ts)
    except InvalidTimestampFormat:
        log.err("Report submitted with invalid timestamp!")
        return False

    # check report IP
    try:
        IPAddress(fields['probe_ip'])
    except ValueError:
        log.err("Report submitted with invalid IP Address!")
        return False

    # all looks good!
    return True

def get_report_header_fields(report_header):
    required_fields = ['probe_asn', 'probe_cc', 'probe_ip', 'start_time',
                       'test_name', 'test_version']
    try:
        return dict([(k,report_header[k]) for k in required_fields ])
    except KeyError:
        return None

def get_target_or_fail(fields, report):
    # set the target filename
    reportFormatVersion = fields['test_version']
    CC                  = fields['probe_cc']
    # XXX: wouldn't hurt to check timestamp for sanity again?
    dateInISO8601Format,__,__ = os.path.basename(report).split('_')
    probeASNumber       = fields['probe_asn']

    # make sure path reportFormatVersion/CC exists
    path = os.path.abspath(report_archive_dir)
    for component in [reportFormatVersion, CC]:
        path = os.path.join(path, component)
        if not os.path.isdir(path):
            try:
                os.mkdir(path, path_permission)
                log.debug("mkdir path: %s" % path)
            except OSError:
                return None

    # if the target file already exists, try to find another filename
    filename = "%s_%s.yamloo" % (dateInISO8601Format, probeASNumber)
    target = os.path.join(path, filename)

    # try to get a unique filename. os.open as used below requires
    # that the file not already exist
    naming_attempts = 1
    while os.path.exists(target) and naming_attempts < retry_attempts:
        filename = "%s_%s.%d.yamloo" % (dateInISO8601Format, probeASNumber,
                                        naming_attempts)
        target = os.path.join(path, filename)
        naming_attempts = naming_attempts + 1

    if naming_attempts >= retry_attempts:
        log.err("Failed getting unique filename %d times; skipping" % i)
        return None
    return target

# grab list of reports
reports = glob.glob(report_source_dir+'/*')
reports_to_archive = filter(filter_reports_by_age, reports)

# iterate over the reports to archive
for report in reports_to_archive:
    log.debug("Parsing report: %s" % report)
    try:
        #XXX: verify that os.fdopen works as expected
        f = os.fdopen(os.open(report, os.O_RDONLY|os.O_EXCL|os.O_NONBLOCK))
    except IOError:
        log.err("Unable to get exclusive lock on %s; skipping" % report)
        continue

    # parse the header and validate it
    yamloo = yaml.safe_load_all(f)
    report_header = yamloo.next()
    fields = get_report_header_fields(report_header)
    if not validate_fields(fields):
        continue

    # get a target filename or fail
    target = get_target_or_fail(fields, report)
    if not target:
        continue

    log.debug("target: %s" % target)

    try:
        #XXX: My system does not have os.O_EXLOCK. Verify this works as is.
        g = os.fdopen(os.open(target, os.O_CREAT|os.O_EXCL|os.O_NONBLOCK))

        os.rename(report, target)
        os.chmod(target, target_permission)
        f.close()
        g.close()

    except IOError:
        # unable to lock the file... still held open?
        log.err("Failed to lock target file. Possible race condition!")
        continue

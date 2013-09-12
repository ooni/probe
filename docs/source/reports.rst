Reports
=======

The reports collected by ooniprobe are stored on
https://ooni.torproject.org/reports/ ``CC`` /

Where ``CC`` is the two letter country code as specified by `ISO 31666-2
<http://en.wikipedia.org/wiki/ISO_3166-2>`_.

For example the reports for Italy (``CC`` is ``it``) of the  may be found in:

https://ooni.torproject.org/reports/IT/


This directory shall contain the various reports for the test using the
following convention:

``testName`` - ``dateInISO8601Format`` - ``probeASNumber`` .yamloo

The date is expressed using `ISO 8601 <http://en.wikipedia.org/wiki/ISO_8601>`_
including seconds and with no ``:`` to delimit hours, minutes, days.

Like so:

``YEAR`` - ``MONTH`` - ``DAY`` T ``HOURS`` ``MINUTES`` ``SECONDS`` Z

Look `here for the up to date list of ISO 8601 country codes
<http://www.iso.org/iso/home/standards/country_codes/country_names_and_code_elements_txt.htm>`_

The time is **always** expressed in UTC.

If a collision is detected then an int (starting with 1) will get appended to
the test.

For example if two report that are created on the first of January 2012 at Noon
(UTC time) sharp from MIT (AS3) will be stored here:

::

  https://ooni.torproject.org/reports/US/2012-01-01T120000Z_AS3.yamloo
  https://ooni.torproject.org/reports/US/2012-01-01T120000Z_AS3.1.yamloo


Note: it is highly unlikely that reports get created with the same exact
timestamp from the same exact ASN. If this does happen it could be index of
some malicious report poisoning attack in progress.


Report format version changelog
===============================

In here shall go details about the major changes to the reporting format.

version 0.1
-----------

Initial format version.

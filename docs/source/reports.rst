Reports
=======

The reports collected by ooniprobe are stored on
https://ooni.torproject.org/reports/`reportFormatVersion`/`CC`/

Where `CC` is the two letter country code as specified by
http://en.wikipedia.org/wiki/ISO_3166-2.

For example the reports for Italy (`CC` is `it`) of the `reportVersion` 0.1 may
be found in:

::
  https://ooni.torproject.org/reports/0.1/IT/


This directory shall contain the various reports for the test using the
following convention:

`ISO8601`-AS`probeASNumber`.yamloo

If a collision is detected then an int (starting with 1) will get appended to
the test.

For example a report that was created on the first of January 2012 at Noon (UTC
time) sharp from MIT (AS3) will be stored here:

::

  https://ooni.torproject.org/reports/0.1/US/2012-01-01T120000Z-AS3.yamloo


Report format version changelog
===============================

In here shall go details about he major changes to the reporting format.

version 0.1
-----------

Initial format version.



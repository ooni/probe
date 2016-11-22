oonireport
==========

Synopsis
--------

**oonireport** [*options*] upload | status [*path to report*]

Description
-----------

:program:`oonireport` is a tool for viewing which ooniprobe
reports have not been submitted to a collector and upload them.


:program:`ooniprobe -i /usr/share/ooni/decks-available/web.yaml`

Options
-------

-d, --default-collector 
    Upload the reports to the default collector that is looked up
    with the canonical bouncer.

-f, --configfile
    Specify the configuration file to use.

-c, --collector
    Specify the collector to upload the result to.

-b, --bouncer
    Specify the bouncer to query for a collector.

    --version

    --help               Display this help and exit.

Commands
--------

**upload**

If no argument is specified all the reports that have not been
submitted will be submitted to either the collector specified as
an option (-c) or to the collector that was previously used.

If a report file is specified then only that report file will be
uploaded

**status**

Outputs all of the reports that are either "not uploaded",
"incomplete" or "pending".

The possible statuses are:

not-created

If it has not been created, because the user specified to not use a
collector.

creation-failed

If we attempted to create the report, but failed to do so either because
the collector does not accept our report or because it was unreachable at the
time.

created

If the report has been successfully created, but has not yet been
closed.

incomplete

If the report has been created, but we have failed to update the
report with some data.

oonireport
----------

This tool is used to upload reports that are stored on the users
filesystem and have not been submitted to a collector. This can be
either because the collector was unreachable when we attempted to
submit the report or because the policy of the collector did not
support the specified test.

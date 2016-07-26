#!/usr/bin/env python
from twisted.internet import task

def ooniprobe(reactor):
    from ooni.ui.cli import runWithDaemonDirector, runWithDirector
    from ooni.ui.cli import setupGlobalOptions

    global_options = setupGlobalOptions(logging=True, start_tor=True,
                                        check_incoherences=True)
    if global_options['queue']:
        return runWithDaemonDirector(global_options)
    else:
        return runWithDirector(global_options)

def run():
    task.react(ooniprobe)

if __name__ == "__main__":
    run()

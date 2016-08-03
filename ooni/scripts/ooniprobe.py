#!/usr/bin/env python
import webbrowser
from multiprocessing import Process

from twisted.internet import task, defer

def ooniprobe(reactor):
    from ooni.ui.cli import runWithDaemonDirector, runWithDirector
    from ooni.ui.cli import setupGlobalOptions, initializeOoniprobe

    global_options = setupGlobalOptions(logging=True, start_tor=True,
                                        check_incoherences=True)
    if global_options['queue']:
        return runWithDaemonDirector(global_options)
    elif global_options['initialize']:
        return initializeOoniprobe(global_options)
    elif global_options['web-ui']:
        from ooni.scripts.ooniprobe_agent import WEB_UI_URL
        from ooni.scripts.ooniprobe_agent import status_agent, start_agent
        if status_agent() != 0:
            p = Process(target=start_agent)
            p.start()
            p.join()
            print("Started ooniprobe-agent")
        webbrowser.open_new(WEB_UI_URL)
        return defer.succeed(None)
    else:
        return runWithDirector(global_options)

def run():
    task.react(ooniprobe)

if __name__ == "__main__":
    run()

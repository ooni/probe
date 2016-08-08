from __future__ import print_function

import os
import time
import signal

from twisted.scripts import twistd
from twisted.python import usage

from ooni.utils import log
from ooni.settings import config
from ooni.agent.agent import AgentService

WEB_UI_PORT = 8842
WEB_UI_URL = "http://127.0.0.1:{0}".format(WEB_UI_PORT)

class StartOoniprobeAgentPlugin:
    tapname = "ooniprobe"

    def makeService(self, so):
        return AgentService(WEB_UI_PORT)

class OoniprobeTwistdConfig(twistd.ServerOptions):
    subCommands = [
        ("StartOoniprobeAgent", None, usage.Options, "ooniprobe agent")
    ]

class StartOptions(usage.Options):
    pass

class StopOptions(usage.Options):
    pass

class StatusOptions(usage.Options):
    pass

class RunOptions(usage.Options):
    pass

class AgentOptions(usage.Options):
    subCommands = [
        ['start', None, StartOptions, "Start the ooniprobe-agent in the "
                                      "background"],
        ['stop', None, StopOptions, "Stop the ooniprobe-agent"],
        ['status', None, StatusOptions, "Show status of the ooniprobe-agent"],
        ['run', None, RunOptions, "Run the ooniprobe-agent in the foreground"]
    ]
    def postOptions(self):
        self.twistd_args = []

def start_agent(options=None):
    config.set_paths()
    config.initialize_ooni_home()
    config.read_config_file()

    os.chdir(config.running_path)

    # Since we are starting the logger below ourselves we make twistd log to
    #  a null log observer
    twistd_args = ['--logger', 'ooni.utils.log.ooniloggerNull']
    twistd_config = OoniprobeTwistdConfig()
    if options is not None:
        twistd_args.extend(options.twistd_args)
    twistd_args.append("StartOoniprobeAgent")
    try:
        twistd_config.parseOptions(twistd_args)
    except usage.error, ue:
        print("ooniprobe: usage error from twistd: {}\n".format(ue))
    twistd_config.loadedPlugins = {
        "StartOoniprobeAgent": StartOoniprobeAgentPlugin()
    }
    print("Starting ooniprobe agent.")
    print("To view the GUI go to %s" % WEB_UI_URL)
    log.start()
    twistd.runApp(twistd_config)
    return 0

def status_agent():
    pidfile = os.path.join(
        config.running_path,
        'twistd.pid'
    )
    if not os.path.exists(pidfile):
        print("ooniprobe-agent is NOT running")
        return  1
    pid = open(pidfile, "r").read()
    pid = int(pid)
    try:
        os.kill(pid, signal.SIG_DFL)
    except OSError, oserr:
        if oserr.errno == 3:
            print("ooniprobe-agent is NOT running")
            return 1
    print("ooniprobe-agent is running")
    return 0

def stop_agent():
    # This function is borrowed from tahoe
    pidfile = os.path.join(
        config.running_path,
        'twistd.pid'
    )
    if not os.path.exists(pidfile):
        print("It seems like ooniprobe-agent is not running")
        return 2
    pid = open(pidfile, "r").read()
    pid = int(pid)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError, oserr:
        if oserr.errno == 3:
            print("No process was running. Cleaning up.")
            # the process didn't exist, so wipe the pid file
            os.remove(pidfile)
            return 2
        else:
            raise
    try:
        os.remove(pidfile)
    except EnvironmentError:
        pass
    start = time.time()
    time.sleep(0.1)
    wait = 40
    first_time = True
    while True:
        # poll once per second until we see the process is no longer running
        try:
            os.kill(pid, 0)
        except OSError:
            print("process %d is dead" % pid)
            return
        wait -= 1
        if wait < 0:
            if first_time:
                print("It looks like pid %d is still running "
                      "after %d seconds" % (pid, (time.time() - start)))
                print("I will keep watching it until you interrupt me.")
                wait = 10
                first_time = False
            else:
                print("pid %d still running after %d seconds" % \
                (pid, (time.time() - start)))
                wait = 10
        time.sleep(1)
    # we define rc=1 to mean "I think something is still running, sorry"
    return 1

def run():
    options = AgentOptions()
    options.parseOptions()

    if options.subCommand == "run":
        options.twistd_args += ("--nodaemon",)

    if options.subCommand == "stop":
        return stop_agent()

    if options.subCommand == "status":
        return status_agent()

    return start_agent(options)

if __name__ == "__main__":
    run()

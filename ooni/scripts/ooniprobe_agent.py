from __future__ import print_function

import os
import sys
import time
import errno
import signal

from twisted.scripts import twistd
from twisted.python import usage

from ooni.utils import log, is_process_running
from ooni.settings import config
from ooni.agent.agent import AgentService
from ooni import __version__


class StartOoniprobeAgentPlugin:
    tapname = "ooniprobe"

    def makeService(self, so):
        return AgentService(config.advanced.webui_port)

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

    synopsis = """%s [options] command
    """ % (os.path.basename(sys.argv[0]),)

    subCommands = [
        ['start', None, StartOptions, "Start the ooniprobe-agent in the "
                                      "background"],
        ['stop', None, StopOptions, "Stop the ooniprobe-agent"],
        ['status', None, StatusOptions, "Show status of the ooniprobe-agent"],
        ['run', None, RunOptions, "Run the ooniprobe-agent in the foreground"]
    ]

    def postOptions(self):
        self.twistd_args = []

    def opt_version(self):
        """
        Display the ooniprobe version and exit.
        """
        print("ooniprobe-agent version:", __version__)
        sys.exit(0)

def start_agent(options=None):
    config.set_paths()
    config.initialize_ooni_home()
    config.read_config_file()

    os.chdir(config.running_path)

    # Since we are starting the logger below ourselves we make twistd log to
    #  a null log observer
    twistd_args = ['--logger', 'ooni.utils.log.ooniloggerNull',
                   '--umask', '022']

    twistd_config = OoniprobeTwistdConfig()
    if options is not None:
        twistd_args.extend(options.twistd_args)
    twistd_args.append("StartOoniprobeAgent")
    try:
        twistd_config.parseOptions(twistd_args)
    except usage.error as ue:
        print("ooniprobe: usage error from twistd: {}\n".format(ue))
        sys.exit(1)
    twistd_config.loadedPlugins = {
        "StartOoniprobeAgent": StartOoniprobeAgentPlugin()
    }

    try:
        get_running_pidfile()
        print("Stop ooniprobe-agent before attempting to start it")
        return 1
    except NotRunning:
        pass

    print("Starting ooniprobe agent.")
    print("To view the GUI go to %s" % config.web_ui_url)
    log.start()
    twistd.runApp(twistd_config)
    return 0


class NotRunning(RuntimeError):
    pass

def get_running_pidfile():
    """
    :return: This pid of the running ooniprobe-agent instance.
    :raises: NotRunning if it's not running
    """
    running_pidfile = None
    for pidfile in [config.system_pid_path, config.user_pid_path]:
        if not os.path.exists(pidfile):
            # Didn't find the pid_file
            continue
        pid = open(pidfile, "r").read()
        pid = int(pid)
        if is_process_running(pid):
            return pidfile
    raise NotRunning

def is_stale_pidfile(pidfile):
    try:
        with open(pidfile) as fd:
            pid = int(fd.read())
    except Exception:
        return False # that's either garbage in the pid-file or a race
    return not is_process_running(pid)

def get_stale_pidfiles():
    return [f for f in [config.system_pid_path, config.user_pid_path] if is_stale_pidfile(f)]

def status_agent():
    try:
        get_running_pidfile()
        print("ooniprobe-agent is running")
        return 0
    except NotRunning:
        print("ooniprobe-agent is NOT running")
        return 1

def do_stop_agent():
    # This function is borrowed from tahoe
    try:
        pidfile = get_running_pidfile()
    except NotRunning:
        print("ooniprobe-agent is NOT running. Nothing to do.")
        return 2

    pid = open(pidfile, "r").read()
    pid = int(pid)
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as ose:
        if ose.errno == errno.ESRCH:
            print("No process was running.") # it's just a race
            return 2
        elif ose.errno == errno.EPERM:
            # The process is owned by root. We assume it's running
            print("ooniprobe-agent is owned by root. We cannot stop it.")
            return 3
        else:
            raise
    # the process wants to clean it's own pidfile itself
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
                print("Sending a SIGKILL and waiting for it to terminate "
                      "until you kill me.")
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError as ose:
                    # Race condition check. It could have dies already. If
                    # so we are happy.
                    if ose.errno == errno.ESRCH:
                        print("process %d is dead" % pid)
                        return
                wait = 10
                first_time = False
            else:
                print("pid %d still running after %d seconds" % \
                (pid, (time.time() - start)))
                wait = 10
        time.sleep(1)
    # we define rc=1 to mean "I think something is still running, sorry"
    return 1

def stop_agent():
    retval = do_stop_agent()
    for pidfile in get_stale_pidfiles():
        try:
            os.remove(pidfile)
            print("Cleaned up stale pidfile {0}".format(pidfile))
        except EnvironmentError:
            print("Failed to delete the pidfile {0}: {1}".format(pidfile, exc))
    return retval

def run():
    options = AgentOptions()
    options.parseOptions()

    if options.subCommand == None:
        print(options)
        return

    if options.subCommand == "stop":
        return stop_agent()

    if options.subCommand == "status":
        return status_agent()

    if options.subCommand == "run":
        options.twistd_args += ("--nodaemon",)

    return start_agent(options)

if __name__ == "__main__":
    run()

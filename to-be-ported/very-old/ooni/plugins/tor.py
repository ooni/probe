import re
import os.path
import signal
import subprocess
import socket
import threading
import time
import logging

from pytorctl import TorCtl

torrc = os.path.join(os.getcwd(),'torrc') #os.path.join(projroot, 'globaleaks', 'tor', 'torrc')
# hiddenservice = os.path.join(projroot, 'globaleaks', 'tor', 'hiddenservice')

class ThreadProc(threading.Thread):
    def __init__(self, cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd
        self.proc = None

    def run(self):
        print "running"
        try:
            self.proc = subprocess.Popen(self.cmd,
                                         shell = False, stdout = subprocess.PIPE,
                                         stderr = subprocess.PIPE)

        except OSError:
           logging.fatal('cannot execute command')

class Tor:
    def __init__(self):
        self.start()

    def check(self):
        conn = TorCtl.connect()
        if conn != None:
            conn.close()
            return True

        return False


    def start(self):
        if not os.path.exists(torrc):
            raise OSError("torrc doesn't exist (%s)" % torrc)

        tor_cmd = ["tor", "-f", torrc]

        torproc = ThreadProc(tor_cmd)
        torproc.run()

        bootstrap_line = re.compile("Bootstrapped 100%: ")

        while True:
            if torproc.proc == None:
                time.sleep(1)
                continue

            init_line = torproc.proc.stdout.readline().strip()

            if not init_line:
                torproc.proc.kill()
                return False

            if bootstrap_line.search(init_line):
                break

        return True

    def stop(self):
        if not self.check():
            return

        conn = TorCtl.connect()
        if conn != None:
            conn.send_signal("SHUTDOWN")
            conn.close()

t = Tor()

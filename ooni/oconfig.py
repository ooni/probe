from ooni.utils import Storage

# XXX move this to an actual configuration file
basic = Storage()
basic.logfile = '/tmp/ooniprobe.log'
advanced = Storage()

advanced.debug = True

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# 
#  +-----------+
#  |  BRIDGET  |
#  |        +--------------------------------------------+
#  +--------| Use a Tor process to test making a Tor     |
#           | connection to a list of bridges or relays. |
#           +--------------------------------------------+
#
# :authors: Isis Lovecruft, Arturo Filasto
# :licence: see included LICENSE
# :version: 0.1.0-alpha

from __future__                 import with_statement
from functools                  import wraps, partial
from random                     import randint
from twisted.python             import usage
from twisted.plugin             import IPlugin
from twisted.internet           import defer, error, reactor
from zope.interface             import implements

from ooni.utils                 import log
from ooni.plugoo.tests          import ITest, OONITest
from ooni.plugoo.assets         import Asset

import os
import signal
import sys


def timer(secs, e=None):
    def decorator(func):
        def _timer(signum, frame):
            raise TimeoutError, e
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _timer)
            signal.alarm(secs)
            try:
                res = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return res
        return wraps(func)(wrapper)
    return decorator


class MissingAssetException(Exception):
    """Raised when neither there are neither bridges nor relays to test."""
    def __init__(self):
        log.msg("Bridget can't run without bridges or relays to test!")
        return sys.exit()

class PTNoBridgesException(Exception):
    """Raised when a pluggable transport is specified, but no bridges."""
    def __init__(self):
        log.msg("Pluggable transport requires the bridges option")
        return sys.exit()

class PTNotFoundException(Exception):
    def __init__(self, transport_type):
        m  = "Pluggable Transport type %s was unaccounted " % transport_type
        m += "for, please contact isis(at)torproject(dot)org and it will "
        m += "get included."
        log.msg("%s" % m)
        return sys.exit()

class ValueChecker(object):
    def port_check(self, number):
        """Check that given ports are in the allowed range."""
        number = int(number)
        if number not in range(1024, 65535):
            raise ValueError("Port out of range")

    sock_check, ctrl_check = port_check, port_check
    allowed                = "must be between 1024 and 65535."
    sock_check.coerceDoc   = "Port to use for Tor's SocksPort, "   +allowed
    ctrl_check.coerceDoc   = "Port to use for Tor's ControlPort, " +allowed

    def uid_check(pluggable_transport):
        """Check that we're not root when trying to use pluggable transports."""
        uid, gid = os.getuid(), os.getgid()
        if uid == 0 and gid == 0:
            log.msg("Error: Running bridget as root with transports not allowed.")
            log.msg("Dropping privileges to normal user...")
            os.setgid(1000)
            os.setuid(1000)

    def dir_check(d):
        """Check that the given directory exists."""
        if not os.isdir(d):
            raise ValueError("%s doesn't exist, or has wrong permissions" % d)

    def file_check(f):
        if not os.isfile(f):
            raise ValueError("%s does not exist, or has wrong permissions" % f)

class RandomPortException(Exception):
    """Raised when using a random port conflicts with configured ports."""
    def __init__(self):
        log.msg("Unable to use random and specific ports simultaneously")
        return sys.exit()

class TimeoutError(Exception):
    """Raised when a timer runs out."""
    pass

class TxtorconImportError(ImportError):
    """Raised when /ooni/lib/txtorcon cannot be imported from."""
    cwd, tx = os.getcwd(), 'lib/txtorcon/torconfig.py'
    try:
        log.msg("Unable to import from ooni.lib.txtorcon")
        if cwd.endswith('ooni'):
            check = os.path.join(cwd, tx)
        else:
            check = os.path.join(cwd, 'ooni/'+tx)
        assert isfile(check)
    except:
        log.msg("Error: Some OONI libraries are missing!")
        log.msg("Please go to /ooni/lib/ and do \"make all\"")

class BridgetArgs(usage.Options):
    """Commandline options."""
    vc = ValueChecker()

    optParameters = [
        ['bridges', 'b', None,
         'File listing bridge IP:ORPorts to test'],
        ['relays', 'f', None,
         'File listing relay IPs to test'],
        ['socks', 's', 9049, None, vc.sock_check],
        ['control', 'c', 9052, None, vc.ctrl_check],
        ['torpath', 'p', None,
         'Path to the Tor binary to use'],
        ['datadir', 'd', None,
         'Tor DataDirectory to use'],
        ['transport', 't', None,
         'Tor ClientTransportPlugin'],
        ['resume', 'r', 0,
         'Resume at this index']]
    optFlags = [['random', 'x', 'Use random ControlPort and SocksPort']]

    def postOptions(self):
        if not self['bridges'] and not self['relays']:
            raise MissingAssetException
        if self['transport']:
            vc.uid_check(self['transport'])
            if not self['bridges']:
                raise PTNoBridgesException
        if self['socks'] or self['control']:
            if self['random']:
                raise RandomPortException
        if self['datadir']:
            vc.dir_check(self['datadir'])
        if self['torpath']:
            vc.file_check(self['torpath'])

class BridgetAsset(Asset):
    """Class for parsing bridget Assets ignoring commented out lines."""
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

    def parse_line(self, line):
        if line.startswith('#'):
            return
        else:
            return line.replace('\n','')

class BridgetTest(OONITest):
    """
    XXX fill me in

    :ivar config: 
        An :class:`ooni.lib.txtorcon.TorConfig` instance.
    :ivar relays:
        A list of all provided relays to test.
    :ivar bridges:
        A list of all provided bridges to test.
    :ivar socks_port:
        Integer for Tor's SocksPort.
    :ivar control_port:
        Integer for Tor's ControlPort.
    :ivar transport:
        String defining the Tor's ClientTransportPlugin, for testing 
        a bridge's pluggable transport functionality.
    :ivar tor_binary:
        Path to the Tor binary to use, e.g. \'/usr/sbin/tor\'
    """
    implements(IPlugin, ITest)

    shortName    = "bridget"
    description  = "Use a Tor process to test connecting to bridges and relays"
    requirements = None
    options      = BridgetArgs
    blocking     = False

    def initialize(self):
        """
        Extra initialization steps. We only want one child Tor process
        running, so we need to deal with most of the TorConfig() only once,
        before the experiment runs.
        """
        self.socks_port      = 9049
        self.control_port    = 9052
        self.circuit_timeout = 90
        self.tor_binary      = '/usr/sbin/tor'
        self.data_directory  = None
        self.use_pt          = False
        self.pt_type         = None

        self.bridges, self.bridges_up, self.bridges_down = ([] for i in range(3))
        self.bridges_remaining  = lambda: len(self.bridges)
        self.bridges_down_count = lambda: len(self.bridges_down)
        self.current_bridge     = None

        self.relays, self.relays_up, self.relays_down = ([] for i in range(3))
        self.relays_remaining   = lambda: len(self.relays)
        self.relays_down_count  = lambda: len(self.relays_down)
        self.current_relay      = None

        def make_asset_list(opt, lst):
            log.msg("Loading information from %s ..." % opt)
            with open(opt) as opt_file:
                for line in opt_file.readlines():
                    if line.startswith('#'):
                        continue
                    else:
                        lst.append(line.replace('\n',''))

        if self.local_options:
            try:
                from ooni.lib.txtorcon import TorConfig
            except ImportError:
                raise TxtorconImportError

            options = self.local_options
            config  = self.config = TorConfig()

            if options['bridges']:
                self.config.UseBridges = 1
                make_asset_list(options['bridges'], self.bridges)

            if options['relays']:
                ## first hop must be in TorState().entry_guards to build circuits
                self.config.EntryNodes = ','.join(relay_list)
                make_asset_list(options['relays'], self.relays)

            if options['socks']:
                self.socks_port = options['socks']
            if options['control']:
                self.control_port = options['control']

            if options['random']:
                log.msg("Using randomized ControlPort and SocksPort ...")
                self.socks_port   = randint(1024, 2**16)
                self.control_port = randint(1024, 2**16)

            if options['torpath']:
                self.tor_binary = options['torpath']

            if self.local_options['datadir']:
                self.data_directory = local_options['datadir']
            else:
                self.data_directory = None

            if options['transport']:
                self.use_pt = True
                log.msg("Using ClientTransportPlugin %s" % options['transport'])
                [self.pt_type, pt_exec] = options['transport'].split(' ', 1)

                ## ClientTransportPlugin transport exec path-to-binary [options]
                ## XXX we need a better way to deal with all PTs
                if self.pt_type == "obfs2":
                    config.ClientTransportPlugin = self.pt_type + " " + pt_exec
                else:
                    raise PTNotFoundException

            self.config.SocksPort            = self.socks_port
            self.config.ControlPort          = self.control_port
            self.config.CookieAuthentication = 1

    def load_assets(self):
        """
        Load bridges and/or relays from files given in user options. Bridges
        should be given in the form IP:ORport. We don't want to load these as
        assets, because it's inefficient to start a Tor process for each one.
        """
        assets = {}
        if self.local_options:
            if self.local_options['bridges']:
                assets.update({'bridge': 
                               BridgetAsset(self.local_options['bridges'])})
            if self.local_options['relays']:
                assets.update({'relay': 
                               BridgetAsset(self.local_options['relays'])})
        return assets

    def experiment(self, args):
        """
        XXX fill me in

        :param args:
            The :class:`BridgetAsset` line currently being used.
        """
        try:
            from tempfile import mkstemp, mkdtemp
            from shutil   import rmtree

            from twisted.internet.endpoints import TCP4ClientEndpoint

            from ooni.utils        import circuit
            from ooni.lib.txtorcon import TorProcessProtocol
            from ooni.lib.txtorcon import TorProtocolFactory
            from ooni.lib.txtorcon import TorConfig, TorState

        except ImportError:
            raise TxtorconImportError

        except TxtorconImportError:
            ## XXX is this something we should add to the reactor?
            sys.exit()

        def bootstrap(ctrl):
            """
            Launch a Tor process with the TorConfig instance returned from
            initialize() and write_torrc().
            """
            conf = TorConfig(ctrl)
            conf.post_bootstrap.addCallback(setup_done).addErrback(setup_fail)
            log.msg("Tor process connected, bootstrapping ...")

        def delete_temp(delete_list):
            """
            Given a list of files or directories to delete, delete all and 
            suppress all errors.
            """
            for temp in delete_list:
                try:
                    os.unlink(temp)
                except OSError:
                    rmtree(temp, ignore_errors=True)

        #@timer(self.circuit_timeout)
        @defer.inlineCallbacks
        def reconfigure_bridge(state, bridge, use_pt=False, pt_type=None):
            """
            Rewrite the Bridge line in our torrc. If use of pluggable
            transports was specified, rewrite the line as:
                Bridge <transport_type> <ip>:<orport>
            Otherwise, rewrite in the standard form.
            """
            log.msg("Current Bridge: %s" % bridge)
            try:
                if use_pt is False:
                    reset_tor = yield state.protocol.set_conf('Bridge', bridge)
                elif use_pt and pt_type is not None:
                    reset_tor = yield state.protocol.set_conf('Bridge', 
                                                          pt_type +' '+ bridge)
                else:
                    raise PTNotFoundException

                controller_response = reset_tor.callback
                if not controller_response:
                    defer.returnValue((state.callback, None))
                else:
                    defer.returnValue((state.callback, controller_response)) 
            except Exception, e:
                log.msg("Reconfiguring torrc Bridge line failed with %s" % bridge)

        def reconfigure_fail(*param):
            log.msg("Reconfiguring TorConfig with parameters %s failed" % param)
            reactor.stop()

        @defer.inlineCallbacks
        def remove_public_relays(state, bridges):
            """
            Remove bridges from our bridge list which are also listed as
            public relays.
            """
            IPs = map(lambda addr: addr.split(':',1)[0], bridges)
            both = set(state.routers.values()).intersection(IPs)

            def __remove_line__(node, bridges=bridges):
                for line in bridges:
                    if line.startswith(node):
                        log.msg("Removing %s because it is a public relay" % node)
                        bridges.remove(line)

            if len(both) > 0:
                try:
                    updated = yield map(lambda node: __remove_line__(node), both)
                    if not updated:
                        ## XXX do these need to be state.callback?
                        defer.returnValue(state)
                    else:
                        defer.returnValue(state)
                except Exception, e:
                    log.msg("Unable to remove public relays from bridge list:\n%s"
                            % both)
                    log.err(e)

        def setup_fail(proto, bridge_list, relay_list):
            log.err("Setup Failed: %s" % proto)
            log.err("We were given bridge list:\n%s\nAnd our relay list:\n%s\n"
                    % (bridge_list, relay_list))
            report.update({'setup_fail': 'FAILED', 
                           'proto': proto, 
                           'bridge_list': bridge_list, 
                           'relay_list': relay_list})
            reactor.stop()

        def setup_done(proto, bridge_list, relay_list):
            log.msg("Setup Complete: %s" % proto)
            state = TorState(proto.tor_protocol)
            state.post_bootstrap.addCallback(state_complete).addErrback(setup_fail)
            if bridge_list is not None:
                state.post_bootstrap.addCallback(remove_public_relays, bridge_list)
            if relay_list is not None:
                raise NotImplemented
            #report.update({'success': args})

        def start_tor(reactor, update, torrc, to_delete, control_port, tor_binary, 
                      data_directory, bridge_list=None, relay_list=None):
            """
            Create a TCP4ClientEndpoint at our control_port, and connect
            it to our reactor and a spawned Tor process. Compare with 
            :meth:`txtorcon.launch_tor` for differences.
            """
            end_point = TCP4ClientEndpoint(reactor, 'localhost', control_port)
            connection_creator = partial(end_point.connect, TorProtocolFactory())
            process_protocol = TorProcessProtocol(connection_creator, updates)
            process_protocol.to_delete = to_delete
            reactor.addSystemEventTrigger('before', 'shutdown', 
                                          partial(delete_temp, to_delete))
            try:
                transport = reactor.spawnProcess(process_protocol, 
                                                 tor_binary,
                                                 args=(tor_binary,'-f',torrc),
                                                 env={'HOME': data_directory},
                                                 path=data_directory)
                transport.closeStdin()
            except RuntimeError, e:
                process_protocol.connected_cb.errback(e)
            finally:
                return process_protocol.connected_cb, bridge_list, relay_list

        def state_complete(state, bridge_list=None, relay_list=None):
            """Called when we've got a TorState."""
            log.msg("We've completely booted up a Tor version %s at PID %d" 
                    % (state.protocol.version, state.tor_pid))

            log.msg("This Tor has the following %d Circuits:" 
                    % len(state.circuits))
            for circ in state.circuits.values():
                log.msg("%s" % circ)

            if bridge_list is not None and relay_list is None:
                return state, bridge_list
            elif bridge_list is None and relay_list is not None:
                raise NotImplemented
            else:
                return state, None

        def state_attach(state, relay_list):
            log.msg("Setting up custom circuit builder...")
            attacher = CustomCircuit(state)
            state.set_attacher(attacher, reactor)
            state.add_circuit_listener(attacher)

            #for circ in state.circuits.values():
            #    for relay in circ.path:
            #        try:
            #            relay_list.remove(relay)
            #        except KeyError:
            #            continue
            ## XXX how do we attach to circuits with bridges?
            d = defer.Deferred()
            attacher.request_circuit_build(d)
            return d

        def state_attach_fail(state):
            log.msg("Attaching custom circuit builder failed.")

        def updates(prog, tag, summary):
            log.msg("%d%%: %s" % (prog, summary))

        def write_torrc(conf, data_dir=None):
            """
            Create a torrc in our data_directory. If we don't yet have a 
            data_directory, create a temporary one. Any temporary files or
            folders are added to delete_list.

            :return: delete_list, data_dir, torrc
            """
            delete_list = []

            if data_dir is None:
                data_dir = mkdtemp(prefix='bridget-tordata')
                delete_list.append(data_dir)
            conf.DataDirectory = data_dir

            (fd, torrc) = mkstemp(dir=data_dir)
            delete_list.append(torrc)
            os.write(fd, conf.create_torrc())
            os.close(fd)
            return torrc, data_dir, delete_list
        

        log.msg("Bridget: initiating test ... ")

        #while self.bridges_remaining() > 0:
        while args['bridge']:

            #self.current_bridge = self.bridges.pop()
            self.current_bridge = args['bridge']
            try:
                self.bridges.remove(self.current_bridge)
            except ValueError, ve:
                log.err(ve)
                
            if self.config.config.has_key('Bridge'):
                log.msg("We now have %d untested bridges..." 
                        % self.bridges_remaining())
                reconf = defer.Deferred()
                reconf.addCallback(reconfigure_bridge, state,
                                   self.current_bridge, self.use_pt,
                                   self.pt_type)
                reconf.addErrback(reconfigure_fail)
                state.chainDeferred(reconf)

            else:
                self.config.Bridge = self.current_bridge
                (torrc, self.data_directory, to_delete) = write_torrc(
                    self.config, self.data_directory)
        
                log.msg("Starting Tor ...")        
                log.msg("Using the following as our torrc:\n%s" 
                        % self.config.create_torrc())
                report = {'tor_config': self.config.create_torrc()}

                state = start_tor(reactor, updates, torrc, to_delete,
                                  self.control_port, self.tor_binary, 
                                  self.data_directory)
                state.addCallback(setup_done)
                state.addErrback(setup_fail)
                state.addBoth(remove_relays, self.bridges)

            return state

            ## XXX see txtorcon.TorControlProtocol.add_event_listener we
            ##     may not need full CustomCircuit class
            ## o if bridges and relays, use one bridge then build a circuit 
            ##   from three relays
            ## o if bridges only, try one bridge at a time, but don't build
            ##   circuits, just return
            ## o if relays only, build circuits from relays
            #else:
            #    try:
            #        state.addCallback(reconfigure_bridge, self.current_bridge, 
            #                          self.use_pt, self.pt_type)
            #        state.addErrback(reconfigure_fail)
            #    except TimeoutError:
            #        log.msg("Adding %s to unreachable bridges..." 
            #                % self.current_bridge)
            #        self.bridges_down.append(self.current_bridge)
            #    else:
            #        log.msg("Adding %s to reachable bridges..." 
            #                % self.current_bridge)
            #        self.bridges_up.append(self.current_bridge)

        reactor.run()
        ## now build circuits


## So that getPlugins() can register the Test:
bridget = BridgetTest(None, None, None)

## ISIS' NOTES
## -----------
## TODO:
##       o  cleanup documentation
##       x  add DataDirectory option
##       x  check if bridges are public relays
##       o  take bridge_desc file as input, also be able to give same
##          format as output
##       x  Add assychronous timout for deferred, so that we don't wait 
##          forever for bridges that don't work.
##       o  Add mechanism for testing through another host

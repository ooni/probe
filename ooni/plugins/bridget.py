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

from __future__             import with_statement
from functools              import partial
from random                 import randint
from twisted.python         import usage
from twisted.plugin         import IPlugin
from twisted.internet       import defer, error, reactor
from zope.interface         import implements

from ooni.utils             import log, date
from ooni.utils.config      import ValueChecker
from ooni.utils.onion       import parse_data_dir
from ooni.utils.onion       import TxtorconImportError
from ooni.utils.onion       import PTNoBridgesException, PTNotFoundException
from ooni.plugoo.tests      import ITest, OONITest
from ooni.plugoo.assets     import Asset, MissingAssetException

import os
import sys


class RandomPortException(Exception):
    """Raised when using a random port conflicts with configured ports."""
    def __init__(self):
        log.msg("Unable to use random and specific ports simultaneously")
        return sys.exit()

class BridgetArgs(usage.Options):
    """Commandline options."""
    global vc
    vc = ValueChecker
        
    allowed = "Port to use for Tor's %s, must be between 1024 and 65535."
    sock_check = vc(allowed % "SocksPort").port_check
    ctrl_check = vc(allowed % "ControlPort").port_check

    optParameters = [
        ['bridges', 'b', None,
         'File listing bridge IP:ORPorts to test'],
        ['relays', 'f', None,
         'File listing relay IPs to test'],
        ['socks', 's', 9049, None, sock_check],
        ['control', 'c', 9052, None, ctrl_check],
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
            raise MissingAssetException(
                "Bridget can't run without bridges or relays to test!")
        if self['transport']:
            vc().uid_check(
                "Can't run bridget as root with pluggable transports!")
            if not self['bridges']:
                raise PTNoBridgesException
        if self['socks'] or self['control']:
            if self['random']:
                raise RandomPortException
        if self['datadir']:
            vc().dir_check(self['datadir'])
        if self['torpath']:
            vc().file_check(self['torpath'])

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
    description  = "Use a Tor process to test connecting to bridges or relays"
    requirements = None
    options      = BridgetArgs
    blocking     = False

    def initialize(self):
        """
        Extra initialization steps. We only want one child Tor process
        running, so we need to deal with most of the TorConfig() only once,
        before the experiment runs.
        """
        self.d = defer.Deferred()

        self.socks_port      = 9049
        self.control_port    = 9052
        self.circuit_timeout = 90
        self.tor_binary      = '/usr/sbin/tor'
        self.data_directory  = None
        self.use_pt          = False
        self.pt_type         = None

        ## XXX we should do report['bridges_up'].append(self.current_bridge)
        self.bridges, self.bridges_up, self.bridges_down = ([] for i in range(3))
        self.bridges_remaining  = lambda: len(self.bridges)
        self.bridges_down_count = lambda: len(self.bridges_down)
        self.current_bridge     = None

        self.relays, self.relays_up, self.relays_down = ([] for i in range(3))
        self.relays_remaining   = lambda: len(self.relays)
        self.relays_down_count  = lambda: len(self.relays_down)
        self.current_relay      = None

        ## Make sure we don't use self.load_assets() for now: 
        self.assets = {}

        def __make_asset_list__(opt, lst):
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
                __make_asset_list__(options['bridges'], self.bridges)

            if options['relays']:
                ## first hop must be in TorState().guards to build circuits
                self.config.EntryNodes = ','.join(relay_list)
                __make_asset_list__(options['relays'], self.relays)

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

            if options['datadir']:
                self.data_directory = parse_data_dir(options['datadir'])
            else:
                self.data_directory = None

            if options['transport']:
                self.use_pt = True
                log.msg("Using ClientTransportPlugin %s" 
                        % options['transport'])
                [self.pt_type, pt_exec] = options['transport'].split(' ', 1)

                ## ClientTransportPlugin transport exec pathtobinary [options]
                ## XXX we need a better way to deal with all PTs
                if self.pt_type == "obfs2":
                    self.config.ClientTransportPlugin = self.pt_type+" "+pt_exec
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
        We cannot use the Asset model, because that model calls
        self.experiment() with the current Assets, which would be one relay
        and one bridge, then it gives the defer.Deferred returned from
        self.experiment() to self.control(), which means that, for each
        (bridge, relay) pair, experiment gets called again, which instantiates
        an additional Tor process that attempts to bind to the same
        ports. Thus, additionally instantiated Tor processes return with
        RuntimeErrors, which break the final defer.chainDeferred.callback(),
        sending it into the errback chain.
    
            if bridges:
                1. configure first bridge line
                2a. configure data_dir, if it doesn't exist
                2b. write torrc to a tempfile in data_dir
                3. start tor                              } if any of these
                4. remove bridges which are public relays } fail, add current
                5. SIGHUP for each bridge                 } bridge to unreach-
                                                          } able bridges.
            if relays:
                1a. configure the data_dir, if it doesn't exist
                1b. write torrc to a tempfile in data_dir
                2. start tor
                3. remove any of our relays which are already part of current 
                   circuits
                4a. attach CustomCircuit() to self.state
                4b. RELAY_EXTEND for each relay } if this fails, add
                                                } current relay to list
                                                } of unreachable relays
                5. 
            if bridges and relays:
                1. configure first bridge line
                2a. configure data_dir if it doesn't exist
                2b. write torrc to a tempfile in data_dir
                3. start tor
                4. remove bridges which are public relays
                5. remove any of our relays which are already part of current
                   circuits
                6a. attach CustomCircuit() to self.state
                6b. for each bridge, build three circuits, with three
                    relays each
                6c. RELAY_EXTEND for each relay } if this fails, add
                                                } current relay to list
                                                } of unreachable relays

        :param args:
            The :class:`BridgetAsset` line currently being used. Except that it
            in Bridget it doesn't, so it should be ignored and avoided.
        """
        try:
            from ooni.utils         import process
            from ooni.utils.onion   import start_tor, remove_public_relays
            from ooni.utils.onion   import setup_done, setup_fail
            from ooni.utils.onion   import CustomCircuit
            from ooni.lib.txtorcon  import TorConfig, TorState
        except ImportError:
            raise TxtorconImportError
        except TxtorconImportError, tie:
            log.err(tie)
            sys.exit()

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
                    reset_tor = yield state.protocol.set_conf('Bridge',
                                                              bridge)
                elif use_pt and pt_type is not None:
                    reset_tor = yield state.protocol.set_conf(
                        'Bridge', pt_type +' '+ bridge)
                else:
                    raise PTNotFoundException

                controller_response = reset_tor.callback
                controller_response.addCallback(reconfigure_done,
                                                bridge,
                                                reachable)
                controller_response.addErrback(reconfigure_fail,
                                               bridge,
                                               reachable)

                #if not controller_response:
                #    defer.returnValue((state.callback, None))
                #else:
                #    defer.returnValue((state.callback, controller_response))
                if controller_response == 'OK':
                    defer.returnValue((state, controller_response))
                else:
                    log.msg("TorControlProtocol responded with error:\n%s"
                            % controller_response)
                    defer.returnValue((state.callback, None))

            except Exception, e:
                log.msg("Reconfiguring torrc with Bridge line %s failed:\n%s"
                        % (bridge, e))
                defer.returnValue((state.callback, e))

        def reconfigure_done(state, bridge, reachable):
            log.msg("Reconfiguring with 'Bridge %s' successful" % bridge)
            reachable.append(bridge)
            return state

        def reconfigure_fail(state, bridge, unreachable):
            log.msg("Reconfiguring TorConfig with parameters %s failed"
                    % state)
            unreachable.append(bridge)
            return state

        def attacher_extend_circuit(attacher, deferred, router):
            ## XXX todo write me
            ## state.attacher.extend_circuit
            raise NotImplemented
            #attacher.extend_circuit

        def state_attach(state, path):
            log.msg("Setting up custom circuit builder...")
            attacher = CustomCircuit(state)
            state.set_attacher(attacher, reactor)
            state.add_circuit_listener(attacher)
            return state

            ## OLD
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
            log.err("Attaching custom circuit builder failed: %s" % state)


        ## Start the experiment
        log.msg("Bridget: initiating test ... ")
        all_of_the_bridges = self.bridges
        all_of_the_relays  = self.relays  ## Local copy of orginal lists

        if self.bridges_remaining() >= 1 and not 'Bridge' in self.config.config:
            ## XXX we should do self.bridges[0] + self.bridges[1:]
            initial_bridge = all_of_the_bridges.pop()
            self.config.Bridge = initial_bridge
            self.config.save()            ## avoid starting several processes
            assert self.config.config.has_key('Bridge'), "NO BRIDGE"

            state = start_tor(self.reactor, self.config, 
                              self.control_port, self.tor_binary, 
                              self.data_directory).addCallbacks(
                setup_done, 
                errback=setup_fail)
            state.addCallback(remove_public_relays, 
                              self.bridges)

            #controller = singleton_semaphore(bootstrap)
            #controller = x().addCallback(singleton_semaphore, tor)
            #controller.addErrback(setup_fail)

            #filter_bridges = remove_public_relays(self.bridges)

        #bootstrap = defer.gatherResults([controller, filter_bridges], 
        #                                consumeErrors=True)
        log.debug("Current callbacks on TorState():\n%s" % state.callbacks)
        log.debug("TorState():\n%s" % state)

        if self.bridges_remaining() > 0:
            all = []
            for bridge in self.bridges:
                #self.current_bridge = bridge
                new = defer.Deferred()
                new.addCallback(reconfigure_bridge, state, bridge, 
                                self.bridges_remaining(),
                                self.bridges_up,
                                self.bridges_down,
                                use_pt=self.use_pt, 
                                pt_type=self.pt_type)
                all.append(new)

        #state.chainDeferred(defer.DeferredList(all))
        #state.chainDeferred(defer.gatherResults(all, consumeErrors=True))
            check_remaining = defer.DeferredList(all, consumeErrors=True)

            #controller.chainDeferred(check_remaining)
            #log.debug("Current callbacks on TorState():\n%s" 
            #          % controller.callbacks)
            state.chainDeferred(check_remaining)

        if self.relays_remaining() > 0:
            while self.relays_remaining() >= 3:
                #path = list(self.relays.pop() for i in range(3))
                #log.msg("Trying path %s" % '->'.join(map(lambda node: 
                #                                         node, path)))
                self.current_relay = self.relays.pop()
                for circ in state.circuits.values():
                    for node in circ.path:
                        if node == self.current_relay:
                            self.relays_up.append(self.current_relay)
                    if len(circ.path) < 3:
                        try:
                            ext = attacher_extend_circuit(state.attacher, circ,
                                                          self.current_relay)
                            ext.addCallback(attacher_extend_circuit_done, 
                                            state.attacher, circ, 
                                            self.current_relay)
                        except Exception, e:
                            log.msg("Extend circuit failed: %s" % e)
                    else:
                        continue

        state.callback(all)
        self.reactor.run()
        #return state

    def startTest(self, args):
        self.start_time = date.now()
        log.msg("Starting %s" % self.shortName)
        self.do_science = self.experiment(args)
        self.do_science.addCallback(self.finished).addErrback(log.err)
        return self.do_science

## So that getPlugins() can register the Test:
bridget = BridgetTest(None, None, None)


## ISIS' NOTES
## -----------
##
## TODO:
##       o  cleanup documentation
##       x  add DataDirectory option
##       x  check if bridges are public relays
##       o  take bridge_desc file as input, also be able to give same
##          format as output
##       x  Add asynchronous timeout for deferred, so that we don't wait 
##          forever for bridges that don't work.
##       o  Add mechanism for testing through another host

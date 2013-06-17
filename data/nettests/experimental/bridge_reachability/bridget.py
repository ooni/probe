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

from __future__           import with_statement
from functools            import partial
from random               import randint

import os
import sys

from twisted.python       import usage
from twisted.internet     import defer, error, reactor

from ooni                 import nettest

from ooni.utils           import log, date
from ooni.utils.config    import ValueChecker

from ooni.utils.onion     import TxtorconImportError
from ooni.utils.onion     import PTNoBridgesException, PTNotFoundException


try:
    from ooni.utils.onion     import parse_data_dir
except:
    log.msg("Please go to /ooni/lib and do 'make txtorcon' to run this test!")

class MissingAssetException(Exception):
    pass

class RandomPortException(Exception):
    """Raised when using a random port conflicts with configured ports."""
    def __init__(self):
        log.msg("Unable to use random and specific ports simultaneously")
        return sys.exit()

class BridgetArgs(usage.Options):
    """Commandline options."""
    allowed = "Port to use for Tor's %s, must be between 1024 and 65535."
    sock_check = ValueChecker(allowed % "SocksPort").port_check
    ctrl_check = ValueChecker(allowed % "ControlPort").port_check

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
            ValueChecker.uid_check(
                "Can't run bridget as root with pluggable transports!")
            if not self['bridges']:
                raise PTNoBridgesException
        if self['socks'] or self['control']:
            if self['random']:
                raise RandomPortException
        if self['datadir']:
            ValueChecker.dir_check(self['datadir'])
        if self['torpath']:
            ValueChecker.file_check(self['torpath'])

class BridgetTest(nettest.NetTestCase):
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
    name    = "bridget"
    author  = "Isis Lovecruft <isis@torproject.org>"
    version = "0.1"
    description   = "Use a Tor process to test connecting to bridges or relays"
    usageOptions = BridgetArgs

    def setUp(self):
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

        def read_from_file(filename):
            log.msg("Loading information from %s ..." % opt)
            with open(filename) as fp:
                lst = []
                for line in fp.readlines():
                    if line.startswith('#'):
                        continue
                    else:
                        lst.append(line.replace('\n',''))
                return lst

        def __count_remaining__(which):
            total, reach, unreach = map(lambda x: which[x],
                                        ['all', 'reachable', 'unreachable'])
            count = len(total) - reach() - unreach()
            return count

        ## XXX should we do report['bridges_up'].append(self.bridges['current'])
        self.bridges = {}
        self.bridges['all'], self.bridges['up'], self.bridges['down'] = \
            ([] for i in range(3))
        self.bridges['reachable']   = lambda: len(self.bridges['up'])
        self.bridges['unreachable'] = lambda: len(self.bridges['down'])
        self.bridges['remaining']   = lambda: __count_remaining__(self.bridges)
        self.bridges['current']     = None
        self.bridges['pt_type']     = None
        self.bridges['use_pt']      = False

        self.relays = {}
        self.relays['all'], self.relays['up'], self.relays['down'] = \
            ([] for i in range(3))
        self.relays['reachable']   = lambda: len(self.relays['up'])
        self.relays['unreachable'] = lambda: len(self.relays['down'])
        self.relays['remaining']   = lambda: __count_remaining__(self.relays)
        self.relays['current']     = None

        if self.localOptions:
            try:
                from txtorcon import TorConfig
            except ImportError:
                raise TxtorconImportError
            else:
                self.config = TorConfig()
            finally:
                options = self.localOptions

            if options['bridges']:
                self.config.UseBridges = 1
                self.bridges['all'] = read_from_file(options['bridges'])
            if options['relays']:
                ## first hop must be in TorState().guards
                # XXX where is this defined?
                self.config.EntryNodes = ','.join(relay_list)
                self.relays['all'] = read_from_file(options['relays'])
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
            if options['transport']:
                ## ClientTransportPlugin transport exec pathtobinary [options]
                ## XXX we need a better way to deal with all PTs
                log.msg("Using ClientTransportPlugin %s" % options['transport'])
                self.bridges['use_pt'] = True
                [self.bridges['pt_type'], pt_exec] = \
                    options['transport'].split(' ', 1)

                if self.bridges['pt_type'] == "obfs2":
                    self.config.ClientTransportPlugin = \
                        self.bridges['pt_type'] + " " + pt_exec
                else:
                    raise PTNotFoundException

            self.config.SocksPort            = self.socks_port
            self.config.ControlPort          = self.control_port
            self.config.CookieAuthentication = 1

    def test_bridget(self):
        """
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
            from ooni.utils.onion   import remove_public_relays, start_tor
            from ooni.utils.onion   import start_tor_filter_nodes
            from ooni.utils.onion   import setup_fail, setup_done
            from ooni.utils.onion   import CustomCircuit
            from ooni.utils.timer   import deferred_timeout, TimeoutError
            from ooni.lib.txtorcon  import TorConfig, TorState
        except ImportError:
            raise TxtorconImportError
        except TxtorconImportError, tie:
            log.err(tie)
            sys.exit()

        def reconfigure_done(state, bridges):
            """
            Append :ivar:`bridges['current']` to the list
            :ivar:`bridges['up'].
            """
            log.msg("Reconfiguring with 'Bridge %s' successful"
                    % bridges['current'])
            bridges['up'].append(bridges['current'])
            return state

        def reconfigure_fail(state, bridges):
            """
            Append :ivar:`bridges['current']` to the list
            :ivar:`bridges['down'].
            """
            log.msg("Reconfiguring TorConfig with parameters %s failed"
                    % state)
            bridges['down'].append(bridges['current'])
            return state

        @defer.inlineCallbacks
        def reconfigure_bridge(state, bridges):
            """
            Rewrite the Bridge line in our torrc. If use of pluggable
            transports was specified, rewrite the line as:
                Bridge <transport_type> <IP>:<ORPort>
            Otherwise, rewrite in the standard form:
                Bridge <IP>:<ORPort>

            :param state:
                A fully bootstrapped instance of
                :class:`ooni.lib.txtorcon.TorState`.
            :param bridges:
                A dictionary of bridges containing the following keys:

                bridges['remaining'] :: A function returning and int for the
                                        number of remaining bridges to test.
                bridges['current']   :: A string containing the <IP>:<ORPort>
                                        of the current bridge.
                bridges['use_pt']    :: A boolean, True if we're testing
                                        bridges with a pluggable transport;
                                        False otherwise.
                bridges['pt_type']   :: If :ivar:`bridges['use_pt'] is True,
                                        this is a string containing the type
                                        of pluggable transport to test.
            :return:
                :param:`state`
            """
            log.msg("Current Bridge: %s" % bridges['current'])
            log.msg("We now have %d bridges remaining to test..."
                    % bridges['remaining']())
            try:
                if bridges['use_pt'] is False:
                    controller_response = yield state.protocol.set_conf(
                        'Bridge', bridges['current'])
                elif bridges['use_pt'] and bridges['pt_type'] is not None:
                    controller_reponse = yield state.protocol.set_conf(
                        'Bridge', bridges['pt_type'] +' '+ bridges['current'])
                else:
                    raise PTNotFoundException

                if controller_response == 'OK':
                    finish = yield reconfigure_done(state, bridges)
                else:
                    log.err("SETCONF for %s responded with error:\n %s"
                            % (bridges['current'], controller_response))
                    finish = yield reconfigure_fail(state, bridges)

                defer.returnValue(finish)

            except Exception, e:
                log.err("Reconfiguring torrc with Bridge line %s failed:\n%s"
                        % (bridges['current'], e))
                defer.returnValue(None)

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

        log.msg("Bridget: initiating test ... ")  ## Start the experiment

        ## if we've at least one bridge, and our config has no 'Bridge' line
        if self.bridges['remaining']() >= 1 \
                and not 'Bridge' in self.config.config:

            ## configure our first bridge line
            self.bridges['current'] = self.bridges['all'][0]
            self.config.Bridge = self.bridges['current']
                                                  ## avoid starting several
            self.config.save()                    ## processes
            assert self.config.config.has_key('Bridge'), "No Bridge Line"

            ## start tor and remove bridges which are public relays
            from ooni.utils.onion import start_tor_filter_nodes
            state = start_tor_filter_nodes(reactor, self.config,
                                           self.control_port, self.tor_binary,
                                           self.data_directory, self.bridges)
            #controller = defer.Deferred()
            #controller.addCallback(singleton_semaphore, tor)
            #controller.addErrback(setup_fail)
            #bootstrap = defer.gatherResults([controller, filter_bridges],
            #                                consumeErrors=True)

            if state is not None:
                log.debug("state:\n%s" % state)
                log.debug("Current callbacks on TorState():\n%s"
                          % state.callbacks)

        ## if we've got more bridges
        if self.bridges['remaining']() >= 2:
            #all = []
            for bridge in self.bridges['all'][1:]:
                self.bridges['current'] = bridge
                #new = defer.Deferred()
                #new.addCallback(reconfigure_bridge, state, self.bridges)
                #all.append(new)
            #check_remaining = defer.DeferredList(all, consumeErrors=True)
            #state.chainDeferred(check_remaining)
                state.addCallback(reconfigure_bridge, self.bridges)

        if self.relays['remaining']() > 0:
            while self.relays['remaining']() >= 3:
                #path = list(self.relays.pop() for i in range(3))
                #log.msg("Trying path %s" % '->'.join(map(lambda node:
                #                                         node, path)))
                self.relays['current'] = self.relays['all'].pop()
                for circ in state.circuits.values():
                    for node in circ.path:
                        if node == self.relays['current']:
                            self.relays['up'].append(self.relays['current'])
                    if len(circ.path) < 3:
                        try:
                            ext = attacher_extend_circuit(state.attacher, circ,
                                                          self.relays['current'])
                            ext.addCallback(attacher_extend_circuit_done,
                                            state.attacher, circ,
                                            self.relays['current'])
                        except Exception, e:
                            log.err("Extend circuit failed: %s" % e)
                    else:
                        continue

        #state.callback(all)
        #self.reactor.run()
        return state

    def disabled_startTest(self, args):
        """
        Local override of :meth:`OONITest.startTest` to bypass calling
        self.control.

        :param args:
            The current line of :class:`Asset`, not used but kept for
            compatibility reasons.
        :return:
            A fired deferred which callbacks :meth:`experiment` and
            :meth:`OONITest.finished`.
        """
        self.start_time = date.now()
        self.d = self.experiment(args)
        self.d.addErrback(log.err)
        self.d.addCallbacks(self.finished, log.err)
        return self.d

## ISIS' NOTES
## -----------
## TODO:
##       x  cleanup documentation
##       x  add DataDirectory option
##       x  check if bridges are public relays
##       o  take bridge_desc file as input, also be able to give same
##          format as output
##       x  Add asynchronous timeout for deferred, so that we don't wait
##       o  Add assychronous timout for deferred, so that we don't wait
##          forever for bridges that don't work.

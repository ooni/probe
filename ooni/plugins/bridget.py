#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# 
#  +-----------+
#  |  BRIDGET  |
#  |        +----------------------------------------------+
#  +--------| Use a slave Tor process to test making a Tor |
#           | connection to a list of bridges or relays.   |
#           +----------------------------------------------+
#
# :authors: Arturo Filasto, Isis Lovecruft
# :licence: see included LICENSE
# :version: 0.1.0-alpha

from __future__             import with_statement
from os                     import getcwd
from os.path                import isfile
from os.path                import join as pj
from twisted.python         import usage
from twisted.plugin         import IPlugin
from twisted.internet       import defer, error, reactor
from zope.interface         import implements

import random
import sys

from ooni.utils             import log
from ooni.plugoo.tests      import ITest, OONITest
from ooni.plugoo.assets     import Asset


def portCheck(number):
    number = int(number)
    if number not in range(1024, 65535):
        raise ValueError("Port out of range")

portCheckAllowed     = "must be between 1024 and 65535."
sockCheck, ctrlCheck = portCheck, portCheck
sockCheck.coerceDoc  = "Port to use for Tor's SocksPort, " + portCheckAllowed
ctrlCheck.coerceDoc  = "Port to use for Tor's ControlPort, " + portCheckAllowed


class BridgetArgs(usage.Options):
    optParameters = [
        ['bridges', 'b', None,
         'File listing bridge IP:ORPorts to test'],
        ['relays', 'f', None,
         'File listing relay IPs to test'],
        ['socks', 's', 9049, None, portCheck],
        ['control', 'c', 9052, None, portCheck],
        ['torpath', 'p', None,
         'Path to the Tor binary to use'],
        ['datadir', 'd', None,
         'Tor DataDirectory to use'],
        ['transport', 't', None, 
         'Tor ClientTransportPlugin'],
        ['resume', 'r', 0,
         'Resume at this index']]
    optFlags = [
        ['random', 'x', 'Use random ControlPort and SocksPort']]

    def postOptions(self):
        if self['transport'] and not self['bridges']:
            e = "Pluggable transport requires the bridges option"
            raise usage.UsageError, e
        if self['socks'] and self['control']:
            if self['random']:
                e = "Unable to use random and specific ports simultaneously"
                raise usage.usageError, e

class BridgetAsset(Asset):
    """
    Class for parsing bridget Assets ignoring commented out lines.
    """
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
    :ivar relay_list:
        A list of all provided relays to test. We have to do this because
        txtorcon.TorState().entry_guards won't build a custom circuit if the
        first hop isn't in the torrc's EntryNodes.
    :ivar bridge_list:
        A list of all provided bridges to test.
    :ivar socks_port:
        Integer for Tor's SocksPort.
    :ivar control_port:
        Integer for Tor's ControlPort.
    :ivar plug_transport:
        String defining the Tor's ClientTransportPlugin, for testing 
        a bridge's pluggable transport functionality.
    :ivar tor_binary:
        Path to the Tor binary to use, e.g. \'/usr/sbin/tor\'
    """
    implements(IPlugin, ITest)

    shortName = "bridget"
    description = "Use a Tor process to test connecting to bridges and relays"
    requirements = None
    options = BridgetArgs
    blocking = False

    def initialize(self):
        """
        Extra initialization steps. We only want one child Tor process
        running, so we need to deal with the creation of TorConfig() only
        once, before the experiment runs.
        """
        self.socks_port     = 9049
        self.control_port   = 9052
        self.tor_binary     = '/usr/sbin/tor'
        self.data_directory = None

        if self.local_options:
            options = self.local_options

            if not options['bridges'] and not options['relays']:
                self.suicide = True
                return

            try:
                from ooni.lib.txtorcon import TorConfig
            except ImportError:
                log.msg ("Bridget: Unable to import from ooni.lib.txtorcon")
                wd, tx = getcwd(), 'lib/txtorcon/torconfig.py'
                chk = pj(wd,tx) if wd.endswith('ooni') else pj(wd,'ooni/'+tx)
                try:
                    assert isfile(chk)
                except:
                    log.msg("Error: Some OONI libraries are missing!")
                    log.msg("Please go to /ooni/lib/ and do \"make all\"")

            self.config = TorConfig()

            if options['bridges']:
                self.config.UseBridges = 1
                
            if options['relays']:
                ## Stupid hack for testing only relays:
                ## Tor doesn't use EntryNodes when UseBridges is enabled, but
                ## config.state.entry_guards needs to include the first hop to
                ## build a custom circuit.
                self.config.EntryNodes = ','.join(relay_list)

            if options['socks']:
                self.socks_port = options['socks']
                
            if options['control']:
                self.control_port = options['control']

            if options['random']:
                log.msg("Using randomized ControlPort and SocksPort ...")
                self.socks_port   = random.randint(1024, 2**16)
                self.control_port = random.randint(1024, 2**16)

            if options['torpath']:
                self.tor_binary = options['torpath']

            if options['datadir']:
                self.config.DataDirectory = options['datadir']

            if options['transport']:
                ## ClientTransportPlugin transport socks4|socks5 IP:PORT
                ## ClientTransportPlugin transport exec path-to-binary [options]
                if not options['bridges']:
                    e = "You must use the bridge option to test a transport."
                    raise usage.UsageError("%s" % e)
                    
                log.msg("Using pluggable transport ...")
                ## XXX fixme there's got to be a better way to check the exec
                assert type(options['transport']) is str
                self.config.ClientTransportPlugin = options['transport']

            self.config.SocksPort   = self.socks_port
            self.config.ControlPort = self.control_port
            self.config.save()

    def load_assets(self):
        """
        Load bridges and/or relays from files given in user options. Bridges
        should be given in the form IP:ORport. We don't want to load these as
        assets, because it's inefficient to start a Tor process for each one.
        """
        assets           = {}
        self.bridge_list = []
        self.relay_list  = []

        ## XXX fix me
        ## we should probably find a more memory nice way to load addresses,
        ## in case the files are really large
        if self.local_options:

            def make_asset_list(opt, lst):
                log.msg("Loading information from %s ..." % opt)
                with open(opt) as opt_file:
                    for line in opt_file.readlines():
                        if line.startswith('#'):
                            continue
                        else:
                            lst.append(line.replace('\n',''))

            if self.local_options['bridges']:
                make_asset_list(self.local_options['bridges'], 
                                self.bridge_list)
                assets.update({'bridges': self.bridge_list})
            if self.local_options['relays']:
                make_asset_list(self.local_options['relays'],
                                self.relay_list)
                assets.update({'relays': self.relay_list})
        return assets

    def experiment(self, args):
        """
        XXX fill me in

        :param args:
            The :class:`ooni.plugoo.asset.Asset <Asset>` line currently being
            used.
        :meth launch_tor:
            Returns a Deferred which callbacks with a
            :class:`ooni.lib.txtorcon.torproto.TorProcessProtocol
            <TorProcessProtocol>` connected to the fully-bootstrapped Tor;
            this has a :class:`ooni.lib.txtorcon.torcontol.TorControlProtocol
            <TorControlProtocol>` instance as .protocol.
        """
        try:
            from ooni.lib.txtorcon import CircuitListenerMixin, IStreamAttacher
            from ooni.lib.txtorcon import TorProtocolFactory, TorConfig, TorState
            from ooni.lib.txtorcon import DEFAULT_VALUE, launch_tor
        except ImportError:
            log.msg("Error: Unable to import from ooni.lib.txtorcon")
            wd, tx = getcwd(), 'lib/txtorcon/torconfig.py'
            chk = pj(wd,tx) if wd.endswith('ooni') else pj(wd,'ooni/'+tx)
            try:
                assert isfile(chk)
            except:
                log.msg("Error: Some OONI libraries are missing!")
                log.msg("       Please go to /ooni/lib/ and do \"make all\"")
                return sys.exit()

        def bootstrap(ctrl):
            """
            Launch a Tor process with the TorConfig instance returned from
            initialize().
            """
            conf = TorConfig(ctrl)
            conf.post_bootstrap.addCallback(setup_done).addErrback(setup_fail)
            log.msg("Tor process connected, bootstrapping ...")

        def reconf_controller(conf, bridge):
            ## if bridges and relays, use one bridge then build a circuit 
            ## from three relays
            conf.Bridge = bridge
            ## XXX do we need a SIGHUP to restart?                

            ## XXX see txtorcon.TorControlProtocol.add_event_listener we
            ## may not need full CustomCircuit class

            ## if bridges only, try one bridge at a time, but don't build
            ## circuits, just return
            ## if relays only, build circuits from relays

        def reconf_fail(args):
            log.msg("Reconfiguring Tor config with args %s failed" % args)
            reactor.stop()

        def setup_fail(args):
            log.msg("Setup Failed.")
            report.update({'failed': args})
            reactor.stop()

        def setup_done(proto):
            log.msg("Setup Complete: %s" % proto)
            state = TorState(proto.tor_protocol)
            state.post_bootstrap.addCallback(state_complete).addErrback(setup_fail)
            report.update({'success': args})

        def updates(prog, tag, summary):
            log.msg("%d%%: %s" % (prog, summary))

        if len(args) == 0:
            log.msg("Bridget can't run without bridges or relays to test!")
            log.msg("Exiting ...")
            return sys.exit()
        else:

            class CustomCircuit(CircuitListenerMixin):
                implements(IStreamAttacher)

                from txtorcon.interface import IRouterContainer
                from txtorcon.interface import ICircuitContainer
            
                def __init__(self, state):
                    self.state = state
                    self.waiting_circuits = []

                def waiting_on(self, circuit):
                    for (circid, d) in self.waiting_circuits:
                        if circuit.id == circid:
                            return true
                    return False

                def circuit_extend(self, circuit, router):
                    "ICircuitListener"
                    if circuit.purpose != 'GENERAL':
                        return
                    if self.waiting_on(circuit):
                        log.msg("Circuit %d (%s)" 
                                % (circuit.id, router.id_hex))

                def circuit_built(self, circuit):
                    "ICircuitListener"
                    if circuit.purpose != 'GENERAL':
                        return
                    log.msg("Circuit %s built ..." % circuit.id)
                    log.msg("Full path of %s: %s" % (circuit.id, circuit.path))
                    for (circid, d) in self.waiting_circuits:
                        if circid == circuit.id:
                            self.waiting_circuits.remove(circid, d)
                            d.callback(circuit)

                def circuit_failed(self, circuit, reason):
                    if self.waiting_on(circuit):
                        log.msg("A circuit we requested %s failed for reason %s" 
                                % (circuit.id, reason))
                        circid, d = None, None
                        for x in self.waiting_circuits:
                            if x[0] == circuit.id:
                                circid, d, stream_cc = x
                        if d is None:
                            raise Exception("Expected to find circuit.")

                        self.waiting_circuits.remove((circid, d))
                        log.msg("Trying to build a circuit for %s" % circid)
                        self.request_circuit_build(d)

                def check_circuit_route(self, circuit, router):
                    if router in circuit.path:
                        #router.update() ## XXX can i use without args? no.
                        TorInfo.dump(self)

                def request_circuit_build(self, deferred):
                    entries = self.state.entry_guards.value()
                    relays  = self.state.routers.values()
                    log.msg("We have these nodes listed as entry guards:") 
                    log.msg("%s" % entries)
                    log.msg("We have these nodes listed as relays:")
                    log.msg("%s" % relays)
                    path = [random.choice(entries),
                            random.choice(relays),
                            random.choice(relays)]
                    log.msg("Requesting a circuit: %s" 
                            % '-->'.join(map(lambda x: x.location.countrycode, 
                                             path)))

                    class AppendWaiting:
                        def __init__(self, attacher, deferred):
                            self.attacher = attacher
                            self.d        = deferred

                        def __call__(self, circuit):
                            """
                            Return from build_circuit is a Circuit, however,
                            we want to wait until it is built before we can
                            issue an attach on it and callback to the Deferred
                            we issue here.
                            """
                            log.msg("Circuit %s is in progress ..." % circuit.id)
                            self.attacher.waiting_circuits.append((circuit.id, 
                                                                   self.d))

                    fin = self.state.build_circuit(path)
                    fin.addCallback(AppendWaiting(self, deferred_to_callback))
                    fin.addErrback(log.err)
                    return fin


            if len(self.bridge_list) >= 1:
                for bridge in self.bridge_list:
                    try:
                        log.msg("Current Bridge: %s" % bridge)
                        reconf_controller(self.config, bridge)
                    except:
                        reconf_fail(bridge)

            log.msg("Bridget: initiating test ... ")
            log.msg("Using the following as our torrc:\n%s" 
                    % self.config.create_torrc())
            report = {'tor_config': self.config.config}
            log.msg("Starting Tor ...")        

            ## :return: a Deferred which callbacks with a TorProcessProtocol
            ##          connected to the fully-bootstrapped Tor; this has a 
            ##          txtorcon.TorControlProtocol instance as .protocol.
            d = launch_tor(self.config, 
                           reactor, 
                           progress_updates=updates,
                           tor_binary=self.tor_binary)
            d.addCallback(bootstrap, self.config)
            d.addErrback(setup_fail)
            ## now build circuits

            #print "Tor process ID: %s" % d.transport.pid
            return d

## So that getPlugins() can register the Test:
bridget = BridgetTest(None, None, None)

## ISIS' NOTES
## -----------
## self.config.save() only needs to be called if Tor is already running.
## 
## to test gid, uid, and euid:
## with open('/proc/self/state') as uidfile:
##     print uidfile.read(1000)
##
## TODO:
##       o  add option for any kwarg=arg self.config setting
##       o  cleanup documentation
##       x  add DataDirectory option
##       o  check if bridges are public relays
##       o  take bridge_desc file as input, also be able to give same
##          format as output
##       o  Add assychronous timout for deferred, so that we don't wait 
##          forever for bridges that don't work.
##       o  Add mechanism for testing through another host
##
## FIX:
##       o  DataDirectory is not found, or permissions aren't right
##       o  Bridge line needs generation of transport properties
##              Bridge <transport> IP:ORPort <fingerprint>

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
These unittests verify that /ooni/utils/packet.py is working correctly.

@authors: Isis Lovecruft <isis@torproject.org>
@version: 0.0.9-alpha
@license: see included LICENCE file
@copyright: (c) 2013 Isis Lovecruft, The Tor Project Inc.
'''

from twisted.trial  import reporter, unittest
from scapy.all      import IP, ICMP, TCP, Packet

from ooni           import runner
from ooni.inputunit import InputUnit
from ooni.reporter  import OReporter
from ooni.templates import scapyt
from ooni.utils     import log, packet


now_many = 3                      ## how_many & resources must always
resources = [('8.8.8.8', 443),    ## be defined *before* the decorator
             ('127.0.0.1', 0),    ## is used, because the output of the
             ('192.168.0.1', 80)] ## decorated function/method is a code
results = reporter.TestResult()   ## object which is generated at runtime.

## Test decorating functions:
@packet.count(how_many)
def icmp_constructor_func_count(input=resources[0]):
    log.debug("Testing @packet.count(how_many) decorator:")
    log.debug("    how_many=%d" % how_many)
    return IP(dst=input[0])/ICMP()

## functions wrapped with @build get the 'input' arg from the decorator
@packet.build(resources)
def icmp_constructor_func_build(input):
    log.debug("Testing @packet.build(resources) decorator:")
    log.debug("    resources=" % resources)
    log.debug("Current resource: %s" % input[0])
    return IP(dst=input[0])/ICMP()

## functions wrapped with @build get the 'input' arg from the decorator
@packet.count(how_many)
@packet.build(resources)
def icmp_constructor_func_both(input):
    log.debug(
        "Testing @packet.count(how_many) @packet.build(resources) decorators:")
    log.debug("    how_many=%d" % how_many)
    log.debug("    resources=" % resources)
    log.debug("Current resource: %s" % input[0])
    return IP(dst=input[0])/ICMP()

@packet.count(how_many)
def tcp_constructor_func_count(input=resources[0], flags='S'):
    (addr, dport) = input
    log.debug("Testing @packet.count(how_many) decorator:")
    log.debug("    how_many=%d" % how_many)
    log.debug("Building packet for %s:%s with flags=%s"
              % (addr, dport, flags))
    return TCP(dport=dport, flags=flags)/IP(dst=addr)

## functions wrapped with @build get the 'input' arg from the decorator
@packet.build(resources)
def tcp_constructor_func_build(input, flags='S'):
    (addr, dport) = input
    log.debug("Testing @packet.build(resources) decorator:")
    log.debug("Building packet for %s:%s with flags=%s"
              % (addr, dport, flags))
    return TCP(dport=dport, flags=flags)/IP(dst=addr)

## functions wrapped with @build get the 'input' arg from the decorator
@packet.count(how_many)
@packet.build(resources)
def tcp_constructor_func_both(input, flags='S'):
    (addr, dport) = input
    log.debug(
        "Testing @packet.count(how_many) @packet.build(resources) decorators:")
    log.debug("    how_many=%d" % how_many)
    log.debug("    resources=" % resources)
    log.debug("Building packet for %s:%s with flags=%s"
              % (addr, dport, flags))
    return TCP(dport=dport, flags=flags)/IP(dst=addr)


class TestPacket(unittest.TestCase):
    log.debug(( "#" * 40 ).join("\n"))
    log.debug("\nTesting packet.py\n")
    log.debug(( "#" * 40 ).join("\n"))

    packet_list = None

    ## Test decoration methods:
    class PacketWithMethods(scapyt.ScapyTest):
        def setUp(self, *args, **kwargs):
            log.debug("Initializing %s" % self.__repr__)

            self.cnt = None
            self.rsrc = None

            if kwargs:
                for key, value in kwargs:
                    log.debug("Setting self.%s = %s" % (key, value))
                    setattr(self, key, value)

            ## because "self.cnt" doesn't get created until initialization,
            ## we must put decorated methods in setUp()
            @packet.count(self.cnt)
            @packet.build(self.rsrc)
            def constructor(self):
                log.debug(
                    "Testing @build(self.rsrc) and @count(self.cnt):")
                log.debug("    self.rsrc = %s" % self.rsrc[0])
                log.debug("    self.cnt = %s" % self.cnt)
                return IP(dst=rsrc[0])/ICMP()

            ## and then add the decorated method to the class afterwards
            self.constructor = constructor

    def run_methods(method_list):
        try:
            assert isinstance(packet_list, list), \
                "icmp_constructor did not return list"
            assert isinstance(method_tester, PacketWithMethods), \
                "method_tester.__class__ is not PacketWithMethods"
            assert len(packet_list) == 3, "wrong number of packets generated"
        except AssertionError, ae:
            log.debug(ae.message)

    def run_functions(function_list):
        for func in function_list:
            try:
                packet_list = func()
                for result in [self.assertIsNotNone(packet_list),
                               self.assertIsInstance(packet_list, list),
                               self.assertIsInstance(packet_list[0], Packet)]:
                    if isinstance(result, Exception):
                        results.addFailure(result)
                    else:
                        results.addSuccess()
            except Exception, exc:
                results.addFailure(exc)
            else:
                results.addSuccess()
                yield packet_list

    def test_function_decoration_with_count(self):
        log.debug(( "~" * 40 ).join("\n"))
        log.debug("Testing @packet.count decorator with function calls...")
        lists = run_functions([icmp_constructor_func_count,
                               tcp_constructor_func_count])
        for packet_list in lists:
            try:
                self.assertEqual(len(packet_list), 3)
            except Exception, exc:
                results.addFailure(exc)
            else:
                results.addSuccess()

    def test_function_decoration_with_build(self):
        log.debug(( "~" * 40 ).join("\n"))
        log.debug("Testing @packet.build decorator with function calls...")
        lists = run_functions([icmp_constructor_func_build,
                               tcp_constructor_func_build])
        for packet_list in lists:
            try:
                self.assertEqual(len(packet_list), 3)
            except Exception, exc:
                results.addFailure(exc)
            else:
                results.addSuccess()

    def test_function_decoration_with_both(self):
        log.debug(( "~" * 40 ).join("\n"))
        log.debug("Testing both decorators with function calls...")
        lists = run_functions([icmp_constructor_func_both,
                               tcp_constructor_func_both])
        for packet_list in lists:
            try:
                self.assertEqual(len(packet_list), 9)
            except Exception, exc:
                results.addFailure(exc)
            else:
                results.addSuccess()

    def test_method_decoration_separately(self):
        log.debug(( "~" * 40 ).join("\n"))
        log.debug("Testing @count and @build separately with method calls...")
        method_tester = PacketWithMethods(cnt=how_many, rsrc=resources)
        lists = run_functions([method_tester.constructor_with_count,
                               method_tester.constructor_with_build])
        for packet_list in lists:
            try:
                self.assertEqual(len(packet_list), 3)
            except Exception, exc:
                results.addFailure(exc)
            else:
                results.addSuccess()

    def test_method_decoration_with_both(self):
        log.debug(( "~" * 40 ).join("\n"))
        log.debug("Testing both decorators with method calls...")
        method_tester = PacketWithMethods(cnt=how_many, rsrc=resources)
        lists = run_functions([method_tester.constructor_with_both])
        for packet_list in lists:
            try:
                self.assertEqual(len(packet_list), 3)
            except Exception, exc:
                results.addFailure(exc)
            else:
                results.addSuccess()

    def test_logging_nicely(self):
        log.debug(( "~" * 40 ).join("\n"))
        log.debug("Testing pretty logging of packets using packet.nicely()...")
        packet_list = tcp_constructor_func_build()
        log.debug("Generated TCP packets:")
        log.debug("\n%s" % '\n'.join([ n for n in packet.nicely(packet_list) ]))

## What are we using to run ooni unittests?

#cmdline_options = {'collector': None}
#input_unit = InputUnit([None])
#test_cases, options = runner.loadTestsAndOptions([TestPacket], cmdline_options)
#oreporter = OReporter(cmdline_options)
#dl = runner.runTestCasesWithInputUnit(test_cases, input_unit,
#                                      oreporter, oreporter)
#@dl.addCallback(done)
#@dl.addErrback(log.err)
#return dl

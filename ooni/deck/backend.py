from twisted.internet import defer

from ooni import errors as e
from ooni.backend_client import guess_backend_type, WebConnectivityClient, \
    CollectorClient
from ooni.utils import log


def sort_addresses_by_priority(priority_address,
                               alternate_addresses,
                               preferred_backend):
    prioritised_addresses = []

    backend_type = guess_backend_type(priority_address)
    priority_address = {
        'address': priority_address,
        'type': backend_type
    }
    # We prefer an onion collector to an https collector to a cloudfront
    # collector to a plaintext collector
    address_priority = ['onion', 'https', 'cloudfront', 'http']
    address_priority.remove(preferred_backend)
    address_priority.insert(0, preferred_backend)

    def filter_by_type(collectors, collector_type):
        return filter(lambda x: x['type'] == collector_type, collectors)

    if (priority_address['type'] != preferred_backend):
        valid_alternatives = filter_by_type(alternate_addresses,
                                            preferred_backend)
        if len(valid_alternatives) > 0:
            alternate_addresses += [priority_address]
            priority_address = valid_alternatives[0]
            alternate_addresses.remove(priority_address)

    prioritised_addresses += [priority_address]
    for address_type in address_priority:
        prioritised_addresses += filter_by_type(alternate_addresses,
                                                address_type)

    return prioritised_addresses


@defer.inlineCallbacks
def get_reachable_test_helper(test_helper_name, test_helper_address,
                              test_helper_alternate, preferred_backend):
    # For the moment we look for alternate addresses only of
    # web_connectivity test helpers.
    if test_helper_name == 'web-connectivity':
        for web_connectivity_settings in sort_addresses_by_priority(
                test_helper_address, test_helper_alternate,
                preferred_backend):
            web_connectivity_test_helper = WebConnectivityClient(
                settings=web_connectivity_settings)
            if not web_connectivity_test_helper.isSupported():
                log.err("Unsupported %s web_connectivity test_helper "
                        "%s" % (
                        web_connectivity_settings['type'],
                        web_connectivity_settings['address']
                ))
                continue
            reachable = yield web_connectivity_test_helper.isReachable()
            if not reachable:
                log.err("Unreachable %s web_connectivity test helper %s" % (
                    web_connectivity_settings['type'],
                    web_connectivity_settings['address']
                ))
                continue
            defer.returnValue(web_connectivity_settings)
        raise e.NoReachableTestHelpers
    else:
        defer.returnValue(test_helper_address.encode('ascii'))


@defer.inlineCallbacks
def get_reachable_collector(collector_address, collector_alternate,
                            preferred_backend):
    for collector_settings in sort_addresses_by_priority(
            collector_address,
            collector_alternate,
            preferred_backend):
        collector = CollectorClient(settings=collector_settings)
        if not collector.isSupported():
            log.err("Unsupported %s collector %s" % (
                        collector_settings['type'],
                        collector_settings['address']))
            continue
        reachable = yield collector.isReachable()
        if not reachable:
            log.err("Unreachable %s collector %s" % (
                        collector_settings['type'],
                        collector_settings['address']))
            continue
        defer.returnValue(collector)

    raise e.NoReachableCollectors


@defer.inlineCallbacks
def get_reachable_test_helpers_and_collectors(net_tests, preferred_backend):
    for net_test in net_tests:
        primary_address = net_test['collector']
        alternate_addresses = net_test.get('collector-alternate', [])
        net_test['collector'] = yield get_reachable_collector(
            primary_address, alternate_addresses, preferred_backend)

        for test_helper_name, test_helper_address in net_test['test-helpers'].items():
             test_helper_alternate = \
                 net_test.get('test-helpers-alternate', {}).get(test_helper_name, [])
             net_test['test-helpers'][test_helper_name] = \
                        yield get_reachable_test_helper(test_helper_name,
                                                        test_helper_address,
                                                        test_helper_alternate,
                                                        preferred_backend)

    defer.returnValue(net_tests)


@defer.inlineCallbacks
def lookup_collector_and_test_helpers(net_test_loaders,
                                      bouncer,
                                      preferred_backend,
                                      no_collector=False):
    required_nettests = []

    requires_test_helpers = False
    requires_collector = False
    for net_test_loader in net_test_loaders:
        nettest = {
            'name': net_test_loader.testName,
            'version': net_test_loader.testVersion,
            'test-helpers': [],
            # XXX deprecate this very soon
            'input-hashes': []
        }
        if not net_test_loader.collector and not no_collector:
            requires_collector = True

        if len(net_test_loader.missingTestHelpers) > 0:
            requires_test_helpers = True
            nettest['test-helpers'] += map(lambda x: x[1],
                                           net_test_loader.missingTestHelpers)

        required_nettests.append(nettest)

    if not requires_test_helpers and not requires_collector:
        defer.returnValue(None)

    print("Using bouncer %s" % bouncer)
    response = yield bouncer.lookupTestCollector(required_nettests)
    try:
        provided_net_tests = yield get_reachable_test_helpers_and_collectors(
            response['net-tests'], preferred_backend)
    except e.NoReachableCollectors:
        log.err("Could not find any reachable collector")
        raise
    except e.NoReachableTestHelpers:
        log.err("Could not find any reachable test helpers")
        raise

    def find_collector_and_test_helpers(test_name, test_version):
        # input_files = [u""+x['hash'] for x in input_files]
        for net_test in provided_net_tests:
            if net_test['name'] != test_name:
                continue
            if net_test['version'] != test_version:
                continue
            # XXX remove the notion of policies based on input file hashes
            # if set(net_test['input-hashes']) != set(input_files):
            #    continue
            return net_test['collector'], net_test['test-helpers']

    for net_test_loader in net_test_loaders:
        log.msg("Setting collector and test helpers for %s" %
                net_test_loader.testName)

        collector, test_helpers = \
            find_collector_and_test_helpers(
                test_name=net_test_loader.testName,
                test_version=net_test_loader.testVersion
                # input_files=net_test_loader.inputFiles
            )

        for option, name in net_test_loader.missingTestHelpers:
            test_helper_address_or_settings = test_helpers[name]
            net_test_loader.localOptions[option] = test_helper_address_or_settings
            net_test_loader.testHelpers[option] = test_helper_address_or_settings

        if not net_test_loader.collector and not no_collector:
            log.debug("Using collector {0}".format(collector))
            net_test_loader.collector = collector

# -*- encoding: utf-8 -*-
import yaml

from twisted.python import usage

from ooni.templates import httpt
from ooni.utils import log

class UsageOptions(usage.Options):
    """
    See https://github.com/hellais/ooni-inputs/processed/uk_mobile_networks_redirects.yaml 
    to see how the rules file should look like.
    """
    optParameters = [
                     ['rules', 'y', None, 
                    'Specify the redirect rules file ']
                    ]

class HTTPUKMobileNetworksTest(httpt.HTTPTest):
    """
    This test was thought of by Open Rights Group and implemented with the
    purpose of detecting censorship in the UK.
    For more details on this test see:
    https://trac.torproject.org/projects/tor/ticket/6437
    XXX port the knowledge from the trac ticket into this test docstring
    """
    name = "HTTP UK mobile network redirect test"

    usageOptions = UsageOptions

    followRedirects = True

    inputFile = ['urls', 'f', None, 'List of urls one per line to test for censorship']
    requiredOptions = ['urls']
    requiresRoot = False
    requiresTor = False

    def testPattern(self, value, pattern, type):
        if type == 'eq':
            return value == pattern
        elif type == 're':
            import re
            if re.match(pattern, value):
                return True
            else:
                return False
        else:
            return None

    def testPatterns(self, patterns, location):
        test_result = False

        if type(patterns) == list:
            for pattern in patterns:
                test_result |= self.testPattern(location, pattern['value'], pattern['type'])
        rules_file = self.localOptions['rules']

        return test_result

    def testRules(self, rules, location):
        result = {}
        blocked = False
        for rule, value in rules.items():
            current_rule = {}
            current_rule['name'] = value['name']
            current_rule['patterns'] = value['patterns']
            current_rule['test'] = self.testPatterns(value['patterns'], location)
            blocked |= current_rule['test']
            result[rule] = current_rule
        result['blocked'] = blocked
        return result

    def processRedirect(self, location):
        self.report['redirect'] = None
        rules_file = self.localOptions['rules']

        fp = open(rules_file)
        rules = yaml.safe_load(fp)
        fp.close()

        log.msg("Testing rules %s" % rules)
        redirect = self.testRules(rules, location)
        self.report['redirect'] = redirect

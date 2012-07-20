"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.protocols import http
from ooni.utils import log

class httptArgs(usage.Options):
    optParameters = [['urls', 'f', None, 'Urls file'],
                     ['url', 'u', 'http://torproject.org/', 'Test single site'],
                     ['resume', 'r', 0, 'Resume at this index'],
                     ['rules', 'y', None, 'Specify the redirect rules file']]

class httptTest(http.HTTPTest):
    implements(IPlugin, ITest)

    shortName = "httpt"
    description = "httpt"
    requirements = None
    options = httptArgs
    blocking = False


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
        else:
            test_result |= self.testPattern(location, patterns['value'], patterns['type'])

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
        self.result['redirect'] = None
        if self.local_options['rules']:
            import yaml
            rules = yaml.load(open(self.local_options['rules']))
            log.msg("Testing rules %s" % rules)
            redirect = self.testRules(rules, location)
            self.result['redirect'] = redirect
        else:
            log.msg("No rules file. Got a redirect, but nothing to do.")


    def control(self, experiment_result, args):
        print self.response
        print self.request
        # What you return here ends up inside of the report.
        log.msg("Running control")
        return {}

    def load_assets(self):
        if self.local_options and self.local_options['urls']:
            return {'url': Asset(self.local_options['urls'])}
        else:
            return {}

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
httpt = httptTest(None, None, None)

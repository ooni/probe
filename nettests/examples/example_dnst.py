from ooni.templates.dnst import DNSTest

class ExampleDNSTest(DNSTest):
    def test_a_lookup(self):
        def gotResult(result):
            # Result is an array containing all the A record lookup results
            print result

        d = self.performALookup('torproject.org', ('8.8.8.8', 53))
        d.addCallback(gotResult)
        return d

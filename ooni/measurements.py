import json

class GenerateResults(object):
    supported_tests = [
        "web_connectivity"
    ]

    def __init__(self, input_file):
        self.input_file = input_file

    def process_web_connectivity(self, entry):
        anomaly = {}
        anomaly['result'] = False
        if entry['test_keys']['blocking'] is not False:
            anomaly['result'] = True
        anomaly['url'] = entry['input']
        return anomaly

    def output(self, output_file):
        results = {}
        with open(self.input_file) as in_file:
            for line in in_file:
                entry = json.loads(line.strip())
                if entry['test_name'] not in self.supported_tests:
                    raise Exception("Unsupported test")
                anomaly = getattr(self, 'process_'+entry['test_name'])(entry)
                results['test_name'] = entry['test_name']
                results['country_code'] = entry['probe_cc']
                results['asn'] = entry['probe_asn']
                results['anomalies'] = results.get('anomalies', [])
                results['anomalies'].append(anomaly)

        with open(output_file, "w") as fw:
            json.dump(results, fw)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: {0} [input_file] [output_file]".format(sys.argv[0]))
        sys.exit(1)
    gr = GenerateResults(sys.argv[1])
    gr.output(sys.argv[2])

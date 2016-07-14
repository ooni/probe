import json

class GenerateResults(object):
    supported_tests = [
        "web_connectivity"
    ]

    def __init__(self, input_file):
        self.input_file = input_file

    def process_web_connectivity(self, entry):
        result = {}
        result['anomaly'] = False
        if entry['test_keys']['blocking'] is not False:
            result['anomaly'] = True
        result['url'] = entry['input']
        return result

    def output(self, output_file):
        results = {}
        with open(self.input_file) as in_file:
            for idx, line in enumerate(in_file):
                entry = json.loads(line.strip())
                if entry['test_name'] not in self.supported_tests:
                    raise Exception("Unsupported test")
                result = getattr(self, 'process_'+entry['test_name'])(entry)
                result['idx'] = idx
                results['test_name'] = entry['test_name']
                results['country_code'] = entry['probe_cc']
                results['asn'] = entry['probe_asn']
                results['results'] = results.get('results', [])
                results['results'].append(result)

        with open(output_file, "w") as fw:
            json.dump(results, fw)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: {0} [input_file] [output_file]".format(sys.argv[0]))
        sys.exit(1)
    gr = GenerateResults(sys.argv[1])
    gr.output(sys.argv[2])

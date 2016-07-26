import json

class Process():
    supported_tests = [
        "web_connectivity"
    ]
    @staticmethod
    def web_connectivity(entry):
        result = {}
        result['anomaly'] = False
        if entry['test_keys']['blocking'] is not False:
            result['anomaly'] = True
        result['url'] = entry['input']
        return result

def generate_summary(input_file, output_file):
    results = {}
    with open(input_file) as in_file:
        for idx, line in enumerate(in_file):
            entry = json.loads(line.strip())
            result = {}
            if entry['test_name'] in Process.supported_tests:
                result = getattr(Process, entry['test_name'])(entry)
            result['idx'] = idx
            results['test_name'] = entry['test_name']
            results['test_start_time'] = entry['test_start_time']
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
    generate_summary(sys.argv[1], sys.argv[2])

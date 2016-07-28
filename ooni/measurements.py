import json
from twisted.python.filepath import FilePath
from ooni.settings import config

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


def list_measurements():
    measurements = []
    measurement_path = FilePath(config.measurements_directory)
    for measurement_id in measurement_path.listdir():
        measurement = measurement_path.child(measurement_id)
        completed = True
        keep = False
        if measurement.child("measurement.njson.progress").exists():
            completed = False
        if measurement.child("keep").exists():
            keep = True
        test_start_time, country_code, asn, test_name = \
            measurement_id.split("-")[:4]
        measurements.append({
            "test_name": test_name,
            "country_code": country_code,
            "asn": asn,
            "test_start_time": test_start_time,
            "id": measurement_id,
            "completed": completed,
            "keep": keep
        })
    return measurements

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: {0} [input_file] [output_file]".format(sys.argv[0]))
        sys.exit(1)
    generate_summary(sys.argv[1], sys.argv[2])

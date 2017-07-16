import json
import operator

from twisted.internet import defer
from twisted.internet.threads import deferToThread
from twisted.python.filepath import FilePath
from ooni.utils import log, is_process_running
from ooni.utils.files import directory_usage
from ooni.settings import config

class MeasurementInProgress(Exception):
    pass

class MeasurementTypes():
    supported_tests = [
        "web_connectivity",
        "http_requests",
        "tcp_connect",
        "http_invalid_request_line",
        "http_header_field_manipulation",
        "facebook_messenger",
        "whatsapp",
        "telegram",
        "vanilla_tor"
    ]

    @staticmethod
    def vanilla_tor(entry):
        result = {}
        result['anomaly'] = False
        if entry['test_keys'].get('success', None) == False:
            result['anomaly'] = True
        return result

    @staticmethod
    def telegram(entry):
        result = {}
        result['anomaly'] = True
        if entry['test_keys'].get('telegram_tcp_blocking', None) == False:
            result['anomaly'] = False
        return result


    @staticmethod
    def whatsapp(entry):
        result = {}
        result['anomaly'] = False
        for key in ['registration_server_status', 'whatsapp_endpoints_status', 'whatsapp_web_status']:
            if entry['test_keys'][key] != 'ok':
                result['anomaly'] = True
        return result

    @staticmethod
    def facebook_messenger(entry):
        result = {}
        result['anomaly'] = False
        true_calc_keys = [
                'facebook_b_api_dns_consistent',
                'facebook_b_api_reachable',
                'facebook_b_graph_dns_consistent',
                'facebook_b_graph_reachable',
                'facebook_edge_dns_consistent',
                'facebook_edge_reachable',
                'facebook_external_cdn_dns_consistent',
                'facebook_external_cdn_reachable',
                'facebook_scontent_cdn_dns_consistent',
                'facebook_scontent_cdn_reachable',
                'facebook_star_dns_consistent',
                'facebook_star_reachable',
                'facebook_stun_dns_consistent',
                # facebook_stun_reachable',
                ]
        false_calc_keys = [
                'facebook_tcp_blocking',
                'facebook_dns_blocking'
                ]
        for key in false_calc_keys:
            if entry['test_keys'][key] == True:
                result['anomaly'] = True
        for key in true_calc_keys:
            if entry['test_keys'][key] == False:
                result['anomaly'] = True
        return result

    @staticmethod
    def http_invalid_request_line(entry):
        result = {}
        result['anomaly'] = False
        if entry['test_keys']['tampering'] == True:
            result['anomaly'] = True
        return result

    @staticmethod
    def http_header_field_manipulation(entry):
        result = {}
        result['anomaly'] = False
        for t in entry['test_keys'].get('tampering', {}).values():
            if t == True:
                result['anomaly'] = True
        return result

    @staticmethod
    def web_connectivity(entry):
        result = {}
        result['anomaly'] = False
        if entry['test_keys']['blocking'] is not False:
            result['anomaly'] = True
            if entry['test_keys']['blocking'] is None:
                result['anomaly_type'] = 'warning'
            else:
                result['anomaly_type'] = 'danger'
        result['url'] = entry['input']
        return result

    @staticmethod
    def tcp_connect(entry):
        result = {}
        result['anomaly'] = False
        if entry['test_keys']['connection'] != "success":
            result['anomaly'] = True
            result['anomaly_type'] = 'danger'
        result['url'] = entry['input']
        return result

    @staticmethod
    def http_requests(entry):
        result = {}
        test_keys = entry['test_keys']
        anomaly = (
            test_keys['body_length_match'] and
            test_keys['headers_match'] and
            (
                test_keys['control_failure'] !=
                test_keys['experiment_failure']
            )
        )
        result['anomaly'] = anomaly
        if anomaly is True:
            result['anomaly_type'] = 'danger'
        result['url'] = entry['input']
        return result


def generate_summary(input_file, output_file, anomaly_file, deck_id='none'):
    results = {}
    anomaly = False
    with open(input_file) as in_file:
        for idx, line in enumerate(in_file):
            entry = json.loads(line.strip())
            result = {}
            if entry['test_name'] in MeasurementTypes.supported_tests:
                result = getattr(MeasurementTypes, entry['test_name'])(entry)
            result['idx'] = idx
            if result.get('anomaly', None) is True:
                anomaly = True
            if not result.get('url', None):
                result['url'] = entry['input']
            results['test_name'] = entry['test_name']
            results['test_start_time'] = entry['test_start_time']
            results['country_code'] = entry['probe_cc']
            results['asn'] = entry['probe_asn']
            results['deck_id'] = deck_id
            results['results'] = results.get('results', [])
            results['results'].append(result)

    with open(output_file, "w") as fw:
        json.dump(results, fw)
    if anomaly is True:
        with open(anomaly_file, 'w') as _: pass
    return results


class MeasurementNotFound(Exception):
    pass


def get_measurement(measurement_id, compute_size=False):
    size = -1
    measurement_path = FilePath(config.measurements_directory)
    measurement = measurement_path.child(measurement_id)
    if not measurement.exists():
        raise MeasurementNotFound

    running = False
    completed = True
    keep = False
    stale = False
    anomaly = False
    if measurement.child("measurements.njson.progress").exists():
        completed = False
        try:
            pid = measurement.child("running.pid").open("r").read()
            pid = int(pid)
            if is_process_running(pid):
                running = True
            else:
                stale = True
        except IOError:
            stale = True

    if measurement.child("keep").exists():
        keep = True

    if measurement.child("anomaly").exists():
        anomaly = True

    if compute_size is True:
        size = directory_usage(measurement.path)

    measurement_metadata = measurement_id.split("-")
    test_start_time, country_code, asn, test_name = measurement_metadata[:4]
    deck_id = "none"
    if len(measurement_metadata) > 4:
        deck_id = '-'.join(measurement_metadata[4:])
    return {
        "test_name": test_name,
        "country_code": country_code,
        "asn": asn,
        "test_start_time": test_start_time,
        "id": measurement_id,
        "completed": completed,
        "keep": keep,
        "running": running,
        "stale": stale,
        "size": size,
        "deck_id": deck_id,
        "anomaly": anomaly
    }


def get_summary(measurement_id):
    """
    Returns a deferred that will fire with the content of the summary
     or will errback with MeasurementInProgress if the measurement has not
     yet finished running.
    """
    measurement_path = FilePath(config.measurements_directory)
    measurement = measurement_path.child(measurement_id)

    if measurement.child("measurements.njson.progress").exists():
        return defer.fail(MeasurementInProgress)

    summary = measurement.child("summary.json")
    anomaly = measurement.child("anomaly")
    if not summary.exists():
        return deferToThread(
            generate_summary,
            measurement.child("measurements.njson").path,
            summary.path,
            anomaly.path
        )

    with summary.open("r") as f:
        return defer.succeed(json.load(f))


def list_measurements(compute_size=False, order=None):
    measurements = []
    measurement_path = FilePath(config.measurements_directory)
    if not measurement_path.exists():
        return measurements
    for measurement_id in measurement_path.listdir():
        try:
            measurements.append(get_measurement(measurement_id, compute_size))
        except Exception as exc:
            log.err("Failed to get metadata for measurement {0}".format(measurement_id))
            log.exception(exc)

    if order is None:
        return measurements

    if order.lower() in ['asc', 'desc']:
        reverse = {'asc': False, 'desc': True}[order.lower()]
        measurements.sort(key=operator.itemgetter('test_start_time'),
                          reverse=reverse)
        return measurements
    else:
        raise ValueError("order must be either 'asc' 'desc' or None")

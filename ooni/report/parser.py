import yaml


class ReportLoader(object):
    _header_keys = (
        'probe_asn',
        'probe_cc',
        'probe_ip',
        'start_time',
        'test_name',
        'test_version',
        'options',
        'input_hashes',
        'software_name',
        'software_version'
    )

    def __init__(self, report_filename):
        self._fp = open(report_filename)
        self._yfp = yaml.safe_load_all(self._fp)

        self.header = self._yfp.next()

    def __iter__(self):
        return self

    def next(self):
        try:
            return self._yfp.next()
        except StopIteration:
            self.close()
            raise StopIteration

    def close(self):
        self._fp.close()

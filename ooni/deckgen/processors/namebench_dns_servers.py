import os
import csv
import GeoIP

from ooni.settings import config


class GeoIPDB(object):
    _borg = {}
    country = None

    def __init__(self):
        self.__dict__ = self._borg
        if not self.country:
            try:
                country_file = config.get_data_file_path('GeoIP/GeoIP.dat')
                self.country = GeoIP.open(country_file,
                                          GeoIP.GEOIP_STANDARD)
            except:
                raise Exception("Edit the geoip_data_dir line in your config"
                                " file to point to your geoip files")


def generate_country_input(country_code, dst):

    csv_file = config.get_data_file_path("resources/"
                                         "namebench-dns-servers.csv")

    filename = os.path.join(dst, "dns-server-%s.txt" % country_code)
    fw = open(filename, "w")
    geoip_db = GeoIPDB()
    reader = csv.reader(open(csv_file))
    for row in reader:
        if row[2] == 'X-Internal-IP':
            continue
        elif row[2] == 'X-Unroutable':
            continue
        elif row[2] == 'X-Link_local':
            continue
        ipaddr = row[0]
        cc = geoip_db.country.country_code_by_addr(ipaddr)
        if not cc:
            continue
        if cc.lower() == country_code.lower():
            fw.write(ipaddr + "\n")
    fw.close()
    return filename


def generate_global_input(dst):
    pass

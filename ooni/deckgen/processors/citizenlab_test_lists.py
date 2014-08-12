import os
import csv
from ooni.settings import config

def generate_country_input(country_code, dst):
    """
    Write to dst/citizenlab-urls-{country_code}.txt
    the list for the given country code.

    Returns:

        the path to the generated input
    """

    country_code = country_code.lower()
    filename = os.path.join(dst, "citizenlab-urls-%s.txt" % country_code)
    fw = open(filename, "w+")

    input_list = os.path.join(config.resources_directory,
                              "citizenlab-test-lists",
                              "test-lists-master",
                              "csv", country_code + ".csv")

    if not os.path.exists(input_list):
        raise Exception("Could not find list for country %s" % country_code)

    with open(input_list) as f:
        csvreader = csv.reader(f)
        csvreader.next()
        for row in csvreader:
            fw.write("%s\n" % row[0])

    fw.close()
    return filename


def generate_global_input(dst):

    filename = os.path.join(dst, "citizenlab-urls-global.txt")
    fw = open(filename, "w+")

    input_list = os.path.join(config.resources_directory,
                              "citizenlab-test-lists",
                              "test-lists-master",
                              "csv", "global.csv")
    with open(input_list) as f:
        csvreader = csv.reader(f)
        csvreader.next()
        for row in csvreader:
            fw.write("%s\n" % row[0])

    fw.close()
    return filename

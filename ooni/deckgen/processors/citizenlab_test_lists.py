import os
import csv
from ooni.settings import config


def load_input(file_input, file_output):
    fw = open(file_output, "w+")
    with open(file_input) as f:
        csvreader = csv.reader(f)
        csvreader.next()
        for row in csvreader:
            fw.write("%s\n" % row[0])
    fw.close()


def generate_country_input(country_code, dst):
    """
    Write to dst/citizenlab-urls-{country_code}.txt
    the list for the given country code.

    Returns:

        the path to the generated input
    """

    country_code = country_code.lower()
    filename = os.path.join(dst, "citizenlab-urls-%s.txt" % country_code)

    input_list = config.get_data_file_path("resources/"
                                           "citizenlab-test-lists/"
                                           + country_code + ".csv")

    if not input_list:
        raise Exception("Could not find list for country %s" % country_code)

    load_input(input_list, filename)

    return filename


def generate_global_input(dst):
    filename = os.path.join(dst, "citizenlab-urls-global.txt")

    input_list = config.get_data_file_path("resources/"
                                           "citizenlab-test-lists/"
                                           "global.csv")

    if not input_list:
        print("Could not find the global input list")
        print("Perhaps you should run ooniresources")
        raise Exception("Could not find the global input list")

    load_input(input_list, filename)

    return filename

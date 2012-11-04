#!/usr/bin/env python
#
# HTTP support for ooni-probe
# by Jacob Appelbaum <jacob@appelbaum.net>
#    Arturo Filasto' <art@fuffa.org>

import ooni.common
import pycurl
import random
import zipfile
import os
from xml.dom import minidom
try:
   from BeautifulSoup import BeautifulSoup
except:
   pass                        # Never mind, let's break later.

def get_random_url(self):
   filepath = os.getcwd() + "/test-lists/top-1m.csv.zip"
   fp = zipfile.ZipFile(filepath, "r")
   fp.open("top-1m.csv")
   content = fp.read("top-1m.csv")
   return "http://" + random.choice(content.split("\n")).split(",")[1]

"""Pick a random header and use that for the request"""
def get_random_headers(self):
  filepath = os.getcwd() + "/test-lists/whatheaders.xml"
  headers = []
  content = open(filepath, "r").read()
  soup = BeautifulSoup(content)
  measurements = soup.findAll('measurement')
  i = random.randint(0,len(measurements))
  for vals in measurements[i].findAll('header'):
    name = vals.find('name').string
    value = vals.find('value').string
    if name != "host":
      headers.append((name, value))
  return headers

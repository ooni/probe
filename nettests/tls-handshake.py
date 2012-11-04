#!/usr/bin/env python

import subprocess
from subprocess import PIPE
serverport = "129.21.124.215:443"
# a subset of those from firefox
ciphers = [
  "ECDHE-ECDSA-AES256-SHA",
  "ECDHE-RSA-AES256-SHA",
  "DHE-RSA-CAMELLIA256-SHA",
  "DHE-DSS-CAMELLIA256-SHA",
  "DHE-RSA-AES256-SHA",
  "DHE-DSS-AES256-SHA",
  "ECDH-ECDSA-AES256-CBC-SHA",
  "ECDH-RSA-AES256-CBC-SHA",
  "CAMELLIA256-SHA",
  "AES256-SHA",
  "ECDHE-ECDSA-RC4-SHA",
  "ECDHE-ECDSA-AES128-SHA",
  "ECDHE-RSA-RC4-SHA",
  "ECDHE-RSA-AES128-SHA",
  "DHE-RSA-CAMELLIA128-SHA",
  "DHE-DSS-CAMELLIA128-SHA"
]
def checkBridgeConnection(host, port)
  cipher_arg = ":".join(ciphers)
  cmd  = ["openssl", "s_client", "-connect", "%s:%s" % (host,port)]
  cmd += ["-cipher", cipher_arg]
  proc = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE,stdin=PIPE)
  out, error = proc.communicate()
  success = "Cipher is DHE-RSA-AES256-SHA" in out
  return success

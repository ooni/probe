#########################################################
# This janky Makefile is Isis' halfassed solution for   #
#    a "one-click" zomg-are-we-there-yet oracle.        #
#                                                       #
#     Obviously, you just do '$ make all'. <(A)3        #
#########################################################

#
#  you'll also need a file of things to test things on.
#  for all of the things.
#

## all tests, without debugging
## ----------------------------
all: echot simplet captivet dnst httphostt squidt

## all tests, with debugging
## -------------------------
## note: you will be doing "n-Ret-n-Ret-n-Ret-s-Ret-n-Ret..."
##       for a *REALLY* long time
all_debug: echod simpled captived dnsd httphostd squidd

simplet:
	../bin/ooniprobe ../nettests/simpletest.py -a ../ooni/assets/hostnames.txt

simpled:
	python -m pdb ../bin/ooniprobe ../nettests/simpletest.py -a ../ooni/assets/hostnames.txt

echot:
	../bin/ooniprobe ../nettests/core/echo.py -f ../ooni/assets/hostnames.txt

echod:
	python -m pdb ../bin/ooniprobe ../nettests/core/echo.py -f ../ooni/assets/hostnames.txt

captivet:
	../bin/ooniprobe ../nettests/core/captiveportal.py -f ../ooni/assets/hostnames.txt

captived:
	python -m pdb ../bin/ooniprobe --spew ../nettests/core/captiveportal.py -f ../ooni/assets/hostnames.txt

dnst:
	../bin/ooniprobe ../nettests/core/dnstamper.py -f ../ooni/assets/hostnames.txt

dnsd:
	python -m pdb ../bin/ooniprobe --spew ../nettests/core/dnstamper.py -f ../ooni/assets/hostnames.txt

squidt:
	../bin/ooniprobe ../nettests/core/squid.py -f ../ooni/assets/hostnames.txt

squidd:
	python -m pdb ../bin/ooniprobe --spew ../nettests/core/squid.py -f ../ooni/assets/hostnames.txt

#mvreports:
#	for $report in `find ../ -name "report*"`; do mv $report test-results #; done

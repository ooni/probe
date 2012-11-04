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
	../bin/ooniprobe ../nettests/simpletest.py -a ../lists/short_hostname_list.txt

simpled:
	python -m pdb ../bin/ooniprobe ../nettests/simpletest.py -a ../lists/short_hostname_list.txt

echot:
	../bin/ooniprobe ../nettests/core/echo.py -f ../lists/short_hostname_list.txt

echod:
	python -m pdb ../bin/ooniprobe -B ../nettests/core/echo.py -f ../lists/short_hostname_list.txt

captivet:
	../bin/ooniprobe ../nettests/core/captiveportal.py -f ../lists/short_hostname_list.txt

captived:
	python -m pdb ../bin/ooniprobe --spew ../nettests/core/captiveportal.py -f ../lists/short_hostname_list.txt

dnst:
	../bin/ooniprobe ../nettests/core/dnstamper.py -f ../lists/short_hostname_list.txt

dnsd:
	python -m pdb ../bin/ooniprobe --spew ../nettests/core/dnstamper.py -f ../lists/short_hostname_list.txt

squidt:
	../bin/ooniprobe ../nettests/core/squid.py -f ../lists/short_hostname_list.txt

squidd:
	python -m pdb ../bin/ooniprobe --spew ../nettests/core/squid.py -f ../lists/short_hostname_list.txt

#mvreports:
#	for $report in `find ../ -name "report*"`; do mv $report test-results #; done

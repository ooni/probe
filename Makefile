#
#  .:| Open Observatory of Network Interference |:.
#
#  /lib/Makefile
#  -------------
#  For obtaining, building, and configuring dependencies for OONI installations.
#
#  @authors: Isis Lovecruft, Arturo Filastó
#  @version: 0.1.0-alpha
#  @license: see included LICENSE file
#  @copyright: 2012 Isis Lovecruft, Arturo Filastó
#
# XXX TODO eventually this should be converted into a distutils setup.py
#

here_we_are = .
top_srcdir = ${here_we_are}

srcdir_ooni = ${top_srcdir}/ooni
srcdir_ooni_kit = ${srcdir_ooni}/kit
srcdir_ooni_plugoo = ${srcdir_ooni}/plugoo
srcdir_ooni_protocols = ${srcdir_ooni}/protocols
srcdir_ooni_templates = ${srcdir_ooni}/templates

srcdir_oonib = ${top_srcdir}/oonib
srcdir_oonib_lib = ${srcdir_oonib}/lib
srcdir_oonib_report = ${srcdir_oonib}/report
srcdir_oonib_report_db = ${srcdir_oonib_report}/db
srcdir_oonib_testhelpers = ${srcdir_oonib}/testhelpers

nettests = ${top_srcdir}/nettests
nettests_core = ${nettests}/core
nettests_examples = ${nettests}/examples
nettests_experimental = ${nettests}/experimental
nettests_third_party = ${nettests}/third_party

prefix = ${top_srcdir}
exec_prefix = ${srcdir_ooni}

bindir = ${top_srcdir}/bin
docsdir = ${top_srcdir}/docs
libdir = ${srcdir_ooni}/lib
includedir = ${top_srcdir}/include
testsdir = ${top_srcdir}/tests

#pkgtwisteddir = $(libdir)/Twisted-*
pkgscapydir = $(libdir)/scapy
pkgtxtorcondir = $(libdir)/txtorcon

SUBDIRS = ${top_srcdir} \
	${srcdir_ooni} \
	${srcdir_ooni_kit} \
	${srcdir_ooni_plugoo} \
	${srcdir_ooni_protocols} \
	${srcdir_ooni_templates} \
	${srcdir_oonib} \
	${srcdir_oonib_lib} \
	${srcdir_oonib_report} \
	${srcdir_oonib_report_db} \
	${srcdir_oonib_testhelpers} \
	${nettests} \
	${nettests_core} \
	${nettests_examples} \
	${nettests_experimental} \
	${nettests_third_party} \
	${pkgscapydir} \
	${pkgtxtorcondir}

all: txtorcon

dependencies: txtorcon non-pip

non-pip: scapy-all

clean:
	rm -rf ${libdir}/txtorcon

clean-all:
	rm -rf ${libdir}/txtorcon
	rm -rf ${libdir}/txtraceroute.py
	rm -rf ${libdir}/txscapy.py
	rm -rf ${libdir}/rfc3339.py

clean-scapy-all:
	rm -rf ${libdir}/scapy*
	rm -rf ${libdir}/pypcap*
	rm -rf ${libdir}/libdnet*

clean-non-pip: clean-scapy-all

clean-dependencies:
	rm -rf ${libdir}/scapy*
	rm -rf ${libdir}/pypcap*
	rm -rf ${libdir}/libdnet*
	rm -rf ${libdir}/txtorcon

txtraceroute:
	echo "Processing dependency txtraceroute..."
	cd ${libdir} && \
		git clone https://github.com/hellais/txtraceroute.git txtraceroute.git && \
		mv txtraceroute.git/txtraceroute.py txtraceroute.py && \
		rm -rf txtraceroute.git && \
		cd ${top_srcdir}

txtorcon:
	echo "Processing dependency txtorcon..."
	cd ${libdir} && \
		git clone https://github.com/meejah/txtorcon.git txtorcon.git && \
		mv txtorcon.git/txtorcon txtorcon && \
		rm -rf txtorcon.git && \
		cd ${top_srcdir}

txscapy:
	echo "Processing dependency txscapy"
	cd ${libdir} && \
		git clone https://github.com/hellais/txscapy.git txscapy.git && \
		mv txscapy.git/txscapy.py txscapy.py && \
		rm -rf txscapy.git && \
		cd ${top_srcdir}

rfc3339:
	echo "Processing RFC3339 dependency"
	cd ${libdir} && \
		hg clone https://bitbucket.org/henry/rfc3339 rfc3339 && \
		mv rfc3339/rfc3339.py rfc3339.py && \
		rm -rf rfc3339 \
		cd ${top_srcdir}

## requires sudo for setup.py:
scapy:
	echo "Processing dependency scapy..."
	cd ${libdir} ; \
		wget --ca-certificate="secdev.org.pem" -O scapy.tar.gz https://www.secdev.org/projects/scapy/files/scapy-latest.tar.gz && \
		tar -xzf scapy.tar.gz && \
		cd scapy-* && sudo python setup.py install && \
		cd .. && rm scapy.tar.gz && cd ${top_srcdir}

## requires sudo for setup.py
pypcap:
	echo "Processing dependency pypcap..."
	cd ${libdir} ; \
		wget -O pypcap.tar.gz https://pypcap.googlecode.com/files/pypcap-1.1.tar.gz && \
		tar -xzf pypcap.tar.gz && cd pypcap-* && \
		sudo python setup.py install && \
		cd .. && rm pypcap.tar.gz && \
		cd ${top_srcdir}
#		make all && make build && make install && make test && \
		make cleandir distclean && cd ${libdir} && \
		rm -rf pypcap*

libdnet:
	echo "Processing dependency libdnet..."
	cd ${libdir} ; \
		wget -O libdnet.tar.gz https://libdnet.googlecode.com/files/libdnet-1.12.tgz && \
		tar -xzf libdnet.tar.gz && cd libdnet-* && \
		configure && make && make install && make clean && \
		cd .. && rm -rf libdnet* && cd ${top_srcdir}

scapy-all: scapy pypcap libdnet

tags-recursive:
	list='$(SUBDIRS)'; for subdir in $$list; do \
	  test "$$subdir" = . || (cd $$subdir && make tags); \
	done

ETAGS = etags
ETAGSFLAGS =
ETAGSARGS =

tags: TAGS

ID: $(HEADERS) $(SOURCES) $(LISP) $(TAGS_FILES)
	list='$(SOURCES) $(HEADERS) $(LISP) $(TAGS_FILES)'; \
	unique=`for i in $$list; do \
	    if test -f "$$i"; then echo $$i; fi; \
	  done | \
	  $(AWK) '    { files[$$0] = 1; } \
	       END { for (i in files) print i; }'`; \
	mkid -fID $$unique

TAGS: tags-recursive $(HEADERS) $(SOURCES)  $(TAGS_DEPENDENCIES) \
		$(TAGS_FILES) $(LISP)
	tags=; \
	here=`pwd`; \
	list='$(SUBDIRS)'; for subdir in $$list; do \
	  if test "$$subdir" = .; then :; else \
	    test -f $$subdir/TAGS && tags="$$tags -i $$here/$$subdir/TAGS"; \
	  fi; \
	done; \
	list='$(SOURCES) $(HEADERS)  $(LISP) $(TAGS_FILES)'; \
	unique=`for i in $$list; do \
	    if test -f "$$i"; fi; \
	  done | \
	  $(AWK) '    { files[$$0] = 1; } \
	       END { for (i in files) print i; }'`; \
	test -z "$(ETAGS_ARGS)$$tags$$unique" \
	  || $(ETAGS) $(ETAGSFLAGS) $(ETAGS_ARGS) \
	     $$tags $$unique

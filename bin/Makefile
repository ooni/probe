# Wrappers for running ooniprobe as a non-root user.
#
# Build-Depends: cython, pythonX.Y-dev, libcap2-bin
# Depends: libpythonX.Y
#
# $ make && make check
# $ sudo make install # after installing the rest of ooni-probe
# $ make installcheck_unsafe # runs complete tests as non-root
#
# `make` builds a program that has file capabilities set on it. This is just
# ./ooniprobe compiled into a C program using Cython, so that one can set
# capabilities directly on the resulting binary. This way, we avoid the need
# for a separate child python interpreter with its own capabilities. Another
# advantage is that libpython.so (needed by the program) would be automatically
# upgraded by the system package manager. The version of python is hard-coded
# into the wrapper at build time; making this dynamic is possible, but much
# more complex and not yet implemented.
#
# Execution may additionally be limited to a particular unix group by using
# chgrp(1) and chmod(1) to 'o-x,g+x' after installation.
#

# GNU Makefile conventions, see https://www.gnu.org/prep/standards/html_node/Makefile-Conventions.html
prefix = /usr/local
exec_prefix = $(prefix)
bindir = $(exec_prefix)/bin

INSTALL = install
PYTHON = python
PYTHON_CONFIG = python-config
CYTHON = cython
SETCAP = setcap

INSTALL_PROGRAM = $(INSTALL)
PY_CFLAGS = $(shell $(PYTHON_CONFIG) --cflags)
PY_LDFLAGS = $(shell $(PYTHON_CONFIG) --ldflags)

BUILDDIR := ./build
SCRIPTDIR := .
TESTDIR := ./test
CAP_SCRIPT := ooniprobe
CAP_NEEDED := cap_net_admin,cap_net_raw

# Unfortunately cython --embed ignores the arguments in the shebang line
# So we need to patch the generated code ourselves.
CYTHON_PRE_MAIN = extern int Py_IgnoreEnvironmentFlag; \
                  Py_IgnoreEnvironmentFlag++; \
                  extern int Py_NoUserSiteDirectory; \
                  Py_NoUserSiteDirectory++;

all: $(BUILDDIR)/$(CAP_SCRIPT)

$(BUILDDIR)/$(CAP_SCRIPT): $(BUILDDIR)/$(CAP_SCRIPT).c Makefile
	$(CC) $(PY_CFLAGS) $(PY_LDFLAGS) "$<" -o "$@"

$(BUILDDIR)/$(CAP_SCRIPT).c: $(SCRIPTDIR)/$(CAP_SCRIPT) Makefile
	mkdir -p "$(BUILDDIR)"
	$(CYTHON) "$<" --embed=CYTHON_MAIN_SENTINEL -Werror -Wextra -o "$@"
	sed -i \
	  -e 's/\(.*CYTHON_MAIN_SENTINEL.*{\)/\1 $(CYTHON_PRE_MAIN)/g' \
	  -e '/CYTHON_MAIN_SENTINEL[^{]*$$/,/{/s/{/{ $(CYTHON_PRE_MAIN)/g' \
	  -e 's/CYTHON_MAIN_SENTINEL/main/g' "$@"

check: $(BUILDDIR)/$(CAP_SCRIPT)
	# test that setcapped binary ignores PYTHONPATH
	BIN="$$(realpath "$<")" && cd "$(TESTDIR)" && PYTHONPATH=. $$BIN --version

install: $(BUILDDIR)/$(CAP_SCRIPT)
	mkdir -p "$(DESTDIR)$(bindir)"
	$(INSTALL_PROGRAM) -t "$(DESTDIR)$(bindir)" "$(BUILDDIR)/$(CAP_SCRIPT)"
	$(SETCAP) "$(CAP_NEEDED)"+eip "$(DESTDIR)$(bindir)/$(CAP_SCRIPT)"

installcheck_unsafe: $(BUILDDIR)/$(CAP_SCRIPT)
	# run a standard check. note that because of hardcoded paths (for security)
	# this can only work after you've installed your development copy
	"./$<" -i /usr/share/ooni/decks/complete.deck

clean:
	rm -rf "$(BUILDDIR)"

.PHONY: clean all check install installcheck%

from __future__ import with_statement
from setuptools import setup, find_packages

def get_requirements():
    with open('requirements.txt', 'r') as f:
        requirements = f.read().splitlines()

    with open('oonib/requirements.txt', 'r') as f:
        requirements += f.read().splitlines()

    # For urls such as https://hg.secdev.org/scapy/archive/tip.zip#egg=scapy in
    # requirements.txt we need to add the package name to install_requires and
    # the entire url to dependency_links. That way setuptools will be able to
    # satisfy the dependency using that url (as long as it is in standard sdist
    # format, a single .py file or an egg).
    pypi_packages = []
    external_links = []
    for package_desc in requirements:
        if '#egg=' in package_desc:
            external_links.append(package_desc)
            pypi_packages.append(package_desc.split('#egg=')[-1])
        else:
            pypi_packages.append(package_desc)

    return pypi_packages, external_links

install_requires, dependency_links = get_requirements()

setup(
    name="ooni-probe",
    version="0.6",
    url="http://ooni.nu/",
    packages=find_packages(),
    scripts=["bin/canary", "bin/oonib", "bin/ooniprobe"],
    install_requires=install_requires,
    dependency_links=dependency_links,
)

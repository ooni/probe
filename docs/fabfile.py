import os
from fabric.api import run, env
from fabric.context_managers import settings
from fabric.operations import sudo, local, put

env.use_ssh_config = True

def update_docs():
    local('make html')
    build_dir = os.path.join(os.getcwd(), 'build', 'html')
    put(build_dir, '/tmp')

    run("sudo -u ooni rm -rf /home/ooni/website/build/docs/")
    run("sudo -u ooni cp -R /tmp/html/ /home/ooni/website/build/docs")

    run("rm -rf /tmp/html")
    update_website()

def update_website():
    run("sudo -u mirroradm /usr/local/bin/static-master-update-component ooni.torproject.org")



#!/bin/bash

[ -f Makefile ] || (echo "Error: must be run from the root of this repo" \
                    && exit 1)

set -e
SSH_KEY=$1

MACHINE_NAME="ooniprobe"

echo "Using SSH Key $SSH_KEY"

(docker-machine status $MACHINE_NAME 2>&1 | grep -q "Host does not exist") && \
    docker-machine create --driver generic \
            --generic-ip-address=$DEPLOY_HOST \
            --generic-ssh-key $SSH_KEY \
            $MACHINE_NAME

# Print out the IP of this machine
docker-machine ip $MACHINE_NAME

# Regenerate certs if there are errors with them
(docker-machine env $MACHINE_NAME) || docker-machine regenerate-certs $MACHINE_NAME

eval "$(docker-machine env ${MACHINE_NAME})"
make docker-run-d
eval $(docker-machine env -u)

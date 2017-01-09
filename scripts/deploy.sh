#!/bin/bash

[ -f Makefile ] || (echo "Error: must be run from the root of this repo" \
                    && exit 1)

set -e
SSH_KEY=$1
MACHINE_NAME="ooniprobe"

if [ $TRAVIS == 'true' ];then
    # Decrypt the travis secrets
    openssl aes-256-cbc -K $encrypted_7943e2e6169a_key \
                        -iv  $encrypted_7943e2e6169a_iv \
                        -in secrets/secrets.tar.enc \
                        -out secrets/secrets.tar -d

    tar xvf secrets/secrets.tar --directory secrets
    mkdir -p $HOME/.ssh/
    mv secrets/id_rsa_travis $HOME/.ssh/

    # Install docker-machine
    curl -L https://github.com/docker/machine/releases/download/v0.8.2/docker-machine-`uname -s`-`uname -m` > docker-machine
    sudo mv docker-machine /usr/local/bin/docker-machine
    sudo chmod +x /usr/local/bin/docker-machine
fi

echo "Using SSH Key $SSH_KEY"

(docker-machine status $MACHINE_NAME 2>&1 | grep -q "Host does not exist") && \
    docker-machine create --driver generic \
            --generic-ip-address=$DEPLOY_HOST \
            --generic-ssh-key $SSH_KEY \
            $MACHINE_NAME

# Print out the IP of this machine
docker-machine ip $MACHINE_NAME

# Regenerate certs if there are errors with them
(docker-machine env $MACHINE_NAME) || docker-machine regenerate-certs -f $MACHINE_NAME

eval "$(docker-machine env ${MACHINE_NAME})"
make docker-run-d
eval $(docker-machine env -u)

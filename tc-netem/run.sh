#!/bin/bash

# set -e

ifconfig eth0 193.167.0.2 netmask 255.255.255.0 up
ifconfig eth1 193.167.100.2 netmask 255.255.255.0 up

ifconfig -a

# We are using eth0 and eth1 as EmuFdNetDevices in ns3.
# Use promiscuous mode to allow ns3 to capture all packets.
ifconfig eth0 promisc
ifconfig eth1 promisc

# A packet arriving at eth0 destined to 10.100.0.0/16 could be routed directly to eth1,
# and a packet arriving at eth1 destined to 10.0.0.0/16 directly to eth0.
# This would allow packets to skip the ns3 simulator altogether.
# Drop those to make sure they actually take the path through ns3.
# iptables -A FORWARD -i eth0 -o eth1 -j DROP
# iptables -A FORWARD -i eth1 -o eth0 -j DROP
# ip6tables -A FORWARD -i eth0 -o eth1 -j DROP
# ip6tables -A FORWARD -i eth1 -o eth0 -j DROP

# if [[ -n "$WAITFORSERVER" ]]; then
#   wait-for-it-quic -t 10s $WAITFORSERVER
# fi

echo "Using scenario:" $SCENARIO

SCENARIONAME=$(echo $SCENARIO | cut -d " " -f1)

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
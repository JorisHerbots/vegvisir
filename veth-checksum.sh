#!/bin/bash

# Source: https://github.com/marten-seemann/quic-network-simulator/blob/master/endpoint/setup.sh
# By default, docker containers don't compute UDP / TCP checksums.
# When packets run through ns3 however, the receiving endpoint requires valid checksums.
# This command makes sure that the endpoints set the checksum on outgoing packets.

DOCKER_BRIDGE=$(ip a | grep "193.167.0.255" | awk 'NF>1{print $NF}')
VETH_IDS=($(ip a | grep "master $DOCKER_BRIDGE" | awk '{sub(/@.*/, ""); print}' | awk 'NF>1{print $NF}'))

for ID in "${VETH_IDS[@]}"
do
	ethtool -K $ID tx off
done

#!/bin/bash

# Set up the routing needed for the simulation
/setup.sh

# The following variables are available for use:
# - ROLE contains the role of this execution context, client or server
# - SERVER_PARAMS contains user-supplied command line parameters
# - CLIENT_PARAMS contains user-supplied command line parameters

echo "ABR: \"$ABR\""
echo "CODEC: \"$CODEC\""
echo "INIT_BUFFER: \"$INIT_BUFFER\""
echo "MAX_BUFFER: \"$MAX_BUFFER\""
echo "MAX_HEIGHT: \"$MAX_HEIGHT\""
echo "STREAM_DURATION: \"$STREAM_DURATION\""
echo "EXP_RATIO: \"$EXP_RATIO\""
echo "STREAM_SPEED: \"$STREAM_SPEED\""

if [[ -z "${ABR}" ]]; then
  ABR="arbiter"
fi

if [[ -z "${CODEC}" ]]; then
  CODEC="h264"
fi

if [[ -z "${INIT_BUFFER}" ]]; then
  INIT_BUFFER="2"
fi

if [[ -z "${MAX_BUFFER}" ]]; then
  MAX_BUFFER="20"
fi

if [[ -z "${MAX_HEIGHT}" ]]; then
  MAX_HEIGHT="1080"
fi

if [[ -z "${EXP_RATIO}" ]]; then
  EXP_RATIO="0.2"
fi

if [[ -z "${STREAM_SPEED}" ]]; then
  STREAM_SPEED="1"
fi

if [[ -n "$STREAM_DURATION" ]]; then
	STREAM_DURATION_STRING="-streamDuration $STREAM_DURATION"
fi

if [ "$ROLE" == "client" ]; then
    # Wait for the simulator to start up.
    /wait-for-it.sh sim:57832 -s -t 30
	REQUESTS_LIST=${REQUESTS// /,}
	# echo "rquesting: [$REQUESTS_LIST]"
    godash -url "[$REQUESTS_LIST]" -adapt $ABR -codec $CODEC -initBuffer $INIT_BUFFER -maxBuffer $MAX_BUFFER -maxHeight $MAX_HEIGHT -expRatio $EXP_RATIO $STREAM_DURATION_STRING -streamSpeed $STREAM_SPEED -QoE on -quic on -storeDASH on -debug on -terminalPrint on -logFile "godash.log" -printHeader "{\"Algorithm\":\"on\",\"Seg_Dur\":\"off\",\"Codec\":\"on\",\"Width\":\"on\",\"Height\":\"on\",\"FPS\":\"off\",\"Play_Pos\":\"off\",\"RTT\":\"off\",\"Seg_Repl\":\"off\",\"Protocol\":\"on\",\"P.1203\":\"on\",\"Clae\":\"on\",\"Duanmu\":\"on\",\"Yin\":\"on\",\"Yu\":\"on\"}" -useTestbed off -serveraddr off -getHeaders off
elif [ "$ROLE" == "server" ]; then
	echo "godash does not support the server role!"
    return 127
fi
#!/bin/bash

current=1

amount=`ls containers | wc -l`

for d in ./containers/*/ ; do
    NAME=$(basename "$d")
	if [[ $(docker images | grep "vegvisir-containers/${NAME}") ]]; then
		echo "$current / $amount: Already built $NAME, skipping"
	else 	
		echo "$current / $amount: building $NAME"
		docker build ./containers/$NAME/ -t "vegvisir-containers/$NAME:latest" &> '/dev/null'
	fi
	current=$(($current+1))
done
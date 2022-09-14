#!/bin/bash

for d in ./containers/*/ ; do
    NAME=$(basename "$d")
	if [[ $(docker images | grep "vegvisir-containers/${NAME}") ]]; then
		echo "Already built $NAME, skipping"
	else 	
		echo "building $NAME"
		docker build ./containers/$NAME/ -t "vegvisir-containers/$NAME:latest"
	fi
done
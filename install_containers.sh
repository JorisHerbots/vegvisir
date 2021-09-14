#!/bin/bash

for d in ./containers/*/ ; do
    NAME=$(basename "$d")
	echo "building $NAME"
	docker build ./containers/$NAME/ -t "vegvisir-containers/$NAME:latest"
done
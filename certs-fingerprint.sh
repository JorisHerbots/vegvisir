#!/bin/bash

set -e

if [ -z "$1" ] ; then
  echo "$0 <cert dir>"
  exit 1
fi

CERTDIR=$1

openssl x509 -in $CERTDIR/cert.pem -pubkey -noout | \
    openssl pkey -pubin -outform der | \
    openssl dgst -sha256 -binary | \
    openssl enc -base64

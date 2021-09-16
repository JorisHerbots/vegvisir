#!/bin/bash

$1 --origin-to-force-quic-on="$2" --enable-experimental-web-platform-features --autoplay-policy=no-user-gesture-required --auto-open-devtools-for-tabs --ignore-certificate-errors-spki-list="$3" "https://$2/dashjs-qlog-abr/demo/demo.html?autosave=true&video=$4"
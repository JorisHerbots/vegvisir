FROM ubuntu:20.04 AS builder

FROM ubuntu:20.04

RUN apt-get update && \
	apt-get install -y net-tools iptables iproute2 tcpdump iputils-ping python && \
	apt-get clean

COPY ./scenarios/ /scenarios/

COPY run.sh .
RUN chmod +x run.sh
RUN mkdir /logs

ENTRYPOINT [ "./run.sh" ]
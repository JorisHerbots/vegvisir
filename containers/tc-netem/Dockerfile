FROM ubuntu:20.04 AS builder

RUN apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get install -y wget

RUN cd / && \
	wget https://dl.google.com/go/go1.15.linux-amd64.tar.gz && \
	tar xfz go1.15.linux-amd64.tar.gz && \
	rm go1.15.linux-amd64.tar.gz

ENV PATH="/go/bin:${PATH}"
COPY wait-for-it-quic /wait-for-it-quic
RUN cd /wait-for-it-quic && go build .

FROM ubuntu:20.04

RUN apt-get update && \
	apt-get install -y net-tools iptables iproute2 tcpdump iputils-ping python && \
	apt-get clean

COPY --from=builder /wait-for-it-quic/wait-for-it-quic /usr/bin

COPY ./scenarios/ /scenarios/

COPY run.sh .
RUN chmod +x run.sh
RUN mkdir /logs

ENTRYPOINT [ "./run.sh" ]
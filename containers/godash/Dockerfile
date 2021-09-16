FROM golang:1.16 as godash-builder

RUN git clone https://github.com/JorisHerbots/godash-qlogabr.git godash && cd /go/godash && git checkout 4149918a45801851994b7db52f65087f6e6b9b2e
RUN cd /go/godash && go mod tidy \
	&& go build

FROM martenseemann/quic-network-simulator-endpoint:latest

RUN apt-get update
RUN apt-get install -y git-core python3 python3-pip
RUN pip install -U pip setuptools

RUN git clone https://github.com/itu-p1203/itu-p1203.git && cd /itu-p1203 && git checkout 8428d1d4111911d0b61072be69dffd284e6a7ada
RUN cd /itu-p1203 && pip3 install -e .

COPY --from=godash-builder /go/godash/godash /bin/godash
COPY --from=godash-builder /go/godash/config/configure.json /configure.json
RUN chmod +x /bin/godash

RUN mkdir -p /files

# copy run script and run it
COPY run_endpoint.sh .
RUN chmod +x run_endpoint.sh
ENTRYPOINT [ "./run_endpoint.sh" ]
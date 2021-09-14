FROM golang:1.16 as godash-builder

RUN git clone https://github.com/JorisHerbots/godash-qlogabr.git godash && cd /go/godash && git checkout 3ba3d01da6d05bae5c6c7b6f5825a76007f5c6fe
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
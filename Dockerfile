FROM xboxdev/nxdk:latest

RUN apk add --no-cache -u \
    python3 \
    py3-pip \
    py3-virtualenv \
    ;

COPY . /src

RUN /usr/bin/python3 -m venv /venv && \
    . /venv/bin/activate && \
    pip3 install --no-cache-dir /src

WORKDIR /work

ENTRYPOINT ["/venv/bin/python3", "-m", "nxdk_pgraph_test_repacker", "-T", "/usr/src/nxdk/tools/extract-xiso/build/extract-xiso"]


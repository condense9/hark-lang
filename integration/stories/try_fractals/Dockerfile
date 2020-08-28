FROM python:3.8

ARG HARK_PKG=hark-lang
ARG HARK_VERSION

COPY hark-lang-*.tar.gz ./

RUN pip install ${HARK_PKG}${HARK_VERSION}

ENV FRACTALS_BUCKET=${FRACTALS_BUCKET}

WORKDIR fractals
COPY examples/fractals .

COPY test.sh .
CMD ./test.sh

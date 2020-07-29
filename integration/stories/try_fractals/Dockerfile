FROM python:3.8

ARG TEAL_PKG=teal-lang
ARG TEAL_VERSION

COPY teal-lang-*.tar.gz ./

RUN pip install ${TEAL_PKG}${TEAL_VERSION}

ENV FRACTALS_BUCKET=${FRACTALS_BUCKET}

WORKDIR fractals
COPY examples/fractals .

COPY test.sh .
CMD ./test.sh

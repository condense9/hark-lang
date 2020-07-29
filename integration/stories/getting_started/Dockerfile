FROM python:3.8

ARG TEAL_PKG=teal-lang
ARG TEAL_VERSION

COPY teal-lang-*.tar.gz ./

RUN pip install ${TEAL_PKG}${TEAL_VERSION}

COPY test.sh .
CMD ./test.sh

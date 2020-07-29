
STORY_NAME := $(shell basename $(shell pwd))
IMAGE_NAME := tealqc_$(STORY_NAME)
CONT_NAME := tealqc_$(STORY_NAME)


# Helpers

-build-teal:
	poetry build -f sdist | tail -n1 | cut -d' ' -f4 > version.txt
	cp "../../../dist/$(shell cat version.txt)" .

-build-local:
	docker build -t $(IMAGE_NAME) --build-arg TEAL_PKG=$(shell cat version.txt) .

-build-pypi:
	touch teal-lang-0.0.0.tar.gz
	docker build -t $(IMAGE_NAME) --build-arg TEAL_VERSION=$(TEAL_VERSION) .

# IMAGE_NAME=$(IMAGE_NAME) CONT_NAME=$(CONT_NAME) docker-compose run tealqc
-run-test:
	docker run --rm -it --env-file ../.env $(IMAGE_NAME)


# Commands

local: -build-teal -build-local -run-test  ## Test the local Teal checkout

local-nobuild: -build-local -run-test  ## Test the local Teal checkout without rebuilding Teal

test: -build-pypi -run-test  ## Test a PyPI release (configure with $TEAL_VERSION)

clean:  ## Remove artefacts
	-rm version.txt
	-rm *.tar.gz
	-docker rm $(IMAGE_NAME)


.PHONY: local-nobuild local clean test

.PHONY: -run-test -build-local -build-pypi -build-teal

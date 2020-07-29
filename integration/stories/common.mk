
STORY_NAME := $(shell basename $(shell pwd))
IMAGE_NAME := tealqc_$(STORY_NAME)
CONT_NAME := tealqc_$(STORY_NAME)


# Helpers

-build-teal:
	poetry build -f sdist | tail -n1 | cut -d' ' -f4 > version.txt
	cp "../../../dist/"$$(< version.txt) .

-build-local:
	test -f version.txt
	docker build -t $(IMAGE_NAME) --build-arg TEAL_PKG=$$(< version.txt) .

-build-pypi:
	touch teal-lang-0.0.0.tar.gz
	docker build -t $(IMAGE_NAME) --build-arg TEAL_VERSION=$(TEAL_VERSION) .

# IMAGE_NAME=$(IMAGE_NAME) CONT_NAME=$(CONT_NAME) docker-compose run tealqc
-run-test:
	docker run --rm -it --env-file ../.env $(IMAGE_NAME)

-copy-examples:
	cp -r ../../../examples .

-clean:
	-rm version.txt
	-rm *.tar.gz
	-docker rm $(IMAGE_NAME)
	-rm -rf examples


# Commands

# If needed, copy the Teal examples folder into the story
ifeq ($(NEED_EXAMPLES),yes)

## Test the local Teal checkout
local: -copy-examples -build-teal -build-local -run-test

## Test the local Teal checkout without rebuilding Teal
local-nobuild: -copy-examples -build-local -run-test

## Test a PyPI release (configure with $TEAL_VERSION)
test: -copy-examples -build-pypi -run-test

else

local: -build-teal -build-local -run-test
local-nobuild: -build-local -run-test
test: -build-pypi -run-test

endif


clean: -clean  ## Remove artefacts


.PHONY: local-nobuild local clean test

.PHONY: -run-test -build-local -build-pypi -build-teal -clean

C9_VERSION = 0.1.0
LIBS = libs
BUILD = build

all: cleansrc pkg/service.py build ## Build everything

pkg/service.py: README.md
	md-tangle -f -v README.md
	black service.py
	mv service.py pkg/service.py

deps:  ## Install runtime Python dependencies
	mkdir -p $(LIBS)
	poetry build
	pip install --upgrade --target $(LIBS) ../../dist/c9-$(C9_VERSION).tar.gz

# We only depend on C9 - this step could be installing requirements.txt
build: pkg/service.py  ## Build the deployment
	c9 --dev --libs=$(LIBS) --output=$(BUILD) compile pkg.service SERVICE pkg

cleansrc:  ## Clean everything except terraform things
	find $(BUILD) ! -path "*/.terraform/*" ! -name "*.tfstate*" -delete

clean:  ## Clean everything (including .terraform, ...)
	rm -rf $(BUILD)
	rm -rf $(LIBS)

deploy:  ## Deploy the service
	chmod +x $(BUILD)/deploy.sh
	cd $(BUILD) && ./deploy.sh

check:  ## Check that infra has been created
	awslocal lambda list-functions
	awslocal dynamodb list-tables

test:  ## Invoke the echo_it function for testing
	awslocal lambda invoke \
		--function-name echo_it \
		--payload '{"hello": "world"}' \
		response.json
	cat response.json
	rm response.json

.PHONY: clean cleansrc deps build deploy check test

# Self documenting!
_PADDING = 20
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'

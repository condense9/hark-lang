
_PADDING = 20
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'


.PHONY: init
init:  ## Set up development environment
	pipenv install


.PHONY: test
test:  ## Run unit tests
	PYTHONPATH=src pytest -v


.PHONY: testx
testx:  ## Run unit tests, stopping after first failure
	PYTHONPATH=src pytest -x -vv


.PHONY: stress
stress:  ## Run unit tests lots of times
	PYTHONPATH=src pytest -vv --count 20

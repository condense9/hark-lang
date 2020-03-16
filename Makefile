
_PADDING = 20
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'


.PHONY: init
init:  ## Set up development environment
	pipenv install


.PHONY: test
test:  ## Run unit tests
	cd test && PYTHONPATH=../src/c9c pytest


_PADDING = 20
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'


.PHONY: init
init:  ## Set up development environment
	pipenv install


.PHONY: test
test:  ## Run unit tests
	pipenv run pytest -v


.PHONY: test-local
test-local:  ## Run local end-to-end tests
	pipenv run pytest -x -v -k [local] test/test_endtoend.py


.PHONY: test-aws
test-aws:  ## Run AWS end-to-end tests (using localstack)
	pipenv run pytest -x -v -k [aws] test/test_endtoend.py


.PHONY: stress
stress:  ## Run local unit tests lots of times
	pipenv run pytest -vv --count 20

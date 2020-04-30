
_PADDING = 20
.PHONY: help
help:
	@printf "\033[35m%-$(_PADDING)s %s\033[0m\n" TARGET EFFECT
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'


default: help  ## show this help


.PHONY: test
test:  ## Run unit tests
	pytest -v

.PHONY: test
testx:  ## Run unit tests, stopping after first failure
	pytest -vv -x


.PHONY: test-local
test-local:  ## Run local end-to-end tests
	pytest -x -v -k [local] test/test_endtoend.py


.PHONY: stress
stress:  ## Run local unit tests lots of times
	pytest -vv --count 20

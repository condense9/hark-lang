
_PADDING = 20
.PHONY: help
help:
	@printf "\033[35m%-$(_PADDING)s %s\033[0m\n" TARGET EFFECT
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'


default: help  ## show this help


.PHONY: test
test:  ## Run all unit tests (including the slow ones!)
	pytest --runslow


.PHONY: testfast
testfast:  ## Run the fast unit tests
	pytest

.PHONY: testx
testx:  ## Run fast unit tests, stopping after first failure
	pytest -vv -x


.PHONY: stress
stress:  ## Run the concurrency unit tests lots of times
	pytest -x -vv -k concurrency --log-level info --show-capture=no --runslow --count 10

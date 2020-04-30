
_PADDING = 20
.PHONY: help
help:
	@printf "\033[35m%-$(_PADDING)s %s\033[0m\n" TARGET EFFECT
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'


default: help  ## show this help


.PHONY: test
test:  ## Run all unit tests (including the slow ones!)
	pytest --runslow


.PHONY: testx
testx:  ## Run unit tests, stopping after first failure
	pytest -vv -x --runslow


.PHONY: testfast
testfast:  ## Run the fast unit tests
	pytest


.PHONY: stress
stress:  ## Run the "examples" unit tests lots of times
	pytest -v --count 20 test/test_examples.py

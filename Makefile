
_PADDING = 20
.PHONY: help
help:
	@printf "\033[35m%-$(_PADDING)s %s\033[0m\n" TARGET EFFECT
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-$(_PADDING)s\033[0m %s\n", $$1, $$2}'


default: help  ## show this help


.PHONY: test
test:  ## Run all unit tests (including the slow ones!)
	pytest --runslow --testddb


.PHONY: lint
lint:  ## check for syntax errors or undefined names
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude src/teal_lang/teal_parser/parser.py --exclude .teal_data
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics --exclude .teal_data


.PHONY: testfast
testfast:  ## Run the fast unit tests
	pytest

.PHONY: testx
testx:  ## Run fast unit tests, stopping after first failure
	pytest -vv -x


.PHONY: stress
stress:  ## Run the concurrency unit tests lots of times
	pytest -x -vv -k concurrency --log-level info --show-capture=no --runslow --count 10

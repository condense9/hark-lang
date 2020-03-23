
all: clean service.py build

service.py: README.md
	md-tangle -f -v README.md
	black service.py

.PHONY: build
build:
	PYTHONPATH=../../src python service.py generate -o build

.phony: clean
clean:
	rm service.py
	rm -rf build

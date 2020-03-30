# https://gist.github.com/istepanov/48285351fa206a0aba92615fb9d632c6

PYTHON_VERSION ?= python3.8

all: build
.PHONY: clean requirements build deps


deps:
	mkdir -p build/site-packages
	pip install --target build/site-packages -r requirements.txt
	cd build/site-packages; zip -g -r ../$(FUNCTION).zip . -x "*__pycache__*"
	cp -r ../../src/c9c build
	cd build; zip -r $(FUNCTION).zip c9c

build: deps build/$(FUNCTION).zip

build/$(FUNCTION).zip:
	zip -g -r $@ . -x "*.DS_Store*" "*.git*" "build*" "Makefile" "requirements.txt"

deploy:
	PYTHONPATH=../../src python ../create.py build/$(FUNCTION).zip


# python ../../generate_requirements.py | grep -v boto > requirements.txt
requirements:
	python ../../generate_requirements.py > requirements.txt

clean:
	rm -rf build
	rm -f requirements.txt

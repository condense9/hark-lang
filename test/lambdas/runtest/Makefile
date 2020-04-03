# https://gist.github.com/istepanov/48285351fa206a0aba92615fb9d632c6

C9C = ../../../bin/c9c

all: clean build deploy
.PHONY: clean requirements src build deploy deps

build: requirements deps src


deps:  ## Dependencies
	mkdir -p build/lib
	pip install --target build/lib -r requirements.txt


src:  ## just the test source
	mkdir -p build/lib
	cp -r ../../../src/c9 build/lib

	cp -r ../../handlers/*.py build
	cp runtest.py build

	rm -f build/runtest.zip
	$(C9C) service build/runtest.py SERVICE -o build/runtest.zip --include-all


deploy:  ## Deploy the zip to AWS
	PYTHONPATH=../../../src python deploy.py

requirements:
	python ../../../generate_requirements.py > requirements.txt

clean:
	rm -rf build
	rm -f requirements.txt

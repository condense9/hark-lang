# https://gist.github.com/istepanov/48285351fa206a0aba92615fb9d632c6

FUNCTION = runtest

all: clean build
.PHONY: clean requirements src build deploy deps

build: requirements deps src


deps:  ## Dependencies
	mkdir -p build/site-packages
	pip install --target build/site-packages -r requirements.txt
	mkdir -p build/lib
	cp -r build/site-packages/*  build/lib
	cd build; zip -g -r $(FUNCTION).zip lib -x "*__pycache__*"


src:  ## just the C9 source
	cp -r ../../../src/c9 build/lib
	rm -rf build/lib/c9/compiler
	cd build; zip -g -r $(FUNCTION).zip lib/c9 -x "*__pycache__*"

	mkdir -p build/src
	cp -r ../../handlers/*.py build/src
	cd build; zip -g -r $(FUNCTION).zip src

	make -C ../../handlers clean all
	mkdir -p build/executables
	cp -r ../../handlers/*.zip build/executables
	cd build; zip -g -r $(FUNCTION).zip executables

	zip -g -r build/$(FUNCTION).zip . -x "*.DS_Store*" "*.git*" "build*" "Makefile" "requirements.txt"


deploy:  ## Deploy the zip to AWS
	PYTHONPATH=../../../src python ../create.py build/$(FUNCTION).zip

requirements:
	python ../../../generate_requirements.py > requirements.txt

clean:
	rm -rf build
	rm -f requirements.txt

# https://gist.github.com/istepanov/48285351fa206a0aba92615fb9d632c6

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
	cp -r ../../src/c9c          build/lib
	cd build; zip -g -r $(FUNCTION).zip lib/c9c -x "*__pycache__*"
	cp -r ../../test/handlers    build
	cd build; zip -g -r $(FUNCTION).zip handlers
	zip -g -r build/$(FUNCTION).zip . -x "*.DS_Store*" "*.git*" "build*" "Makefile" "requirements.txt"

deploy:
	PYTHONPATH=../../src python ../create.py build/$(FUNCTION).zip

# python ../../generate_requirements.py | grep -v boto > requirements.txt
requirements:
	python ../../generate_requirements.py > requirements.txt

clean:
	rm -rf build
	rm -f requirements.txt

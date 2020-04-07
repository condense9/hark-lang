#C9 = python -m c9.cli.main
C9 = c9
all: build


build:  ## Build the service deployment
	rm -rf build
	$(C9) compile src.service SERVICE -o build

c9:  ## Just C9 libs
	mkdir -p lib
	cp -r ../../src/c9 lib

deps: c9  ## All dependencies
	mkdir -p lib
	pip install --no-deps --target lib -r requirements.txt

clean:
	rm -rf lib
	rm -rf build

deploy:
	cd build/lambda_code/; zip -r ../lambda.zip . -x "*__pycache__*"
	python deploy.py

.PHONY: clean deps c9 build deploy

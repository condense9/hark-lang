
all: cleansrc pkg/service.py build

pkg/service.py: README.md
	md-tangle -f -v README.md
	black service.py
	mkdir -p pkg
	mv service.py pkg/service.py

build:
	mkdir -p pkg
	touch pkg/__init__.py
	c9 compile pkg.service SERVICE -o build

cleansrc:  ## Clean non-hidden files in build
	rm -rf build/*

clean:  ## Clean everything (including .terraform, ...)
	rm -rf pkg build

deploy:  ## deploy the service
	chmod +x build/deploy.sh
	cd build; ./deploy.sh

.PHONY: clean cleansrc build deploy

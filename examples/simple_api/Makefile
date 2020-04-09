
all: cleansrc pkg/service.py build

pkg/service.py: README.md
	md-tangle -f -v README.md
	black service.py
	mv service.py pkg/service.py

build: pkg/service.py
	c9 compile pkg.service SERVICE -o build

cleansrc:  ## Clean everything except terraform things
	find build -type f ! -path "*/.terraform/*" ! -name "*.tfstate*" -delete

clean:  ## Clean everything (including .terraform, ...)
	rm -rf build

deploy:  ## deploy the service
	chmod +x build/deploy.sh
	cd build && ./deploy.sh

.PHONY: clean cleansrc build deploy

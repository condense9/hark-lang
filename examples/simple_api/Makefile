
all: clean service.py

service.py: README.md
	md-tangle -f -v README.md
	black service.py

# TODO build with c9c

.phony: clean
clean:
	rm service.py
	rm -rf build

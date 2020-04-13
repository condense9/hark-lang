# Getting Started

C9 is a Python 3.8 library and CLI application, and it's probably best to
install it in a virtual environment for your project.

Once installed, check:

```shell
$ c9 --version
```

Have a quick look at the usage (particularly, look at the `compile` command).

```shell
$ c9 --help
```


## Developer Workflow

This is a starting point project layout for a simple ETL service:

```
my_etl/
├── Makefile
├── README.md
├── requirements.txt
├── my_etl
│   ├── __init__.py
│   ├── lib.py
│   └── service.py
└── test
    ├── __init__.py
    ├── test_service.py
    └── test_lib.py
```

| File                 | Purpose                                               |
|----------------------|-------------------------------------------------------|
| Makefile             | (optional) a set of scripts to coordinate the project |
| my_etl/lib.py        | Implementations of functions required by the service  |
| my_etl/service.py    | Implementation of the C9 Service                      |
| test/test_lib.py     | The usual unit tests tests                            |
| test/test_service.py | Integration tests for the service                     |
| requirements.txt     | Python pip requirements                               |


The C9 Service must be defined in a Python package ("`my_etl`" above), and must
define the service name and the handlers to include:

```python
# service.py
import c9
from . import lib

# ... define handlers

SERVICE = c9.Service("My ETL service", handlers=[...])
```

There is a bit of manual work involved in building the service, primarily
because C9 doesn't define how to manage your Python dependencies. The `--libs`
parameter for `c9 compile` specifies where to find your dependencies.

Here's an example `Makefile` to accomplish that:

```makefile
DEV ?= --dev

default: build

deps:  ## Install runtime Python dependencies
	mkdir -p pip_libs
	pip install --upgrade --target pip_libs -r requirements.txt

build:  ## Build the deployment
	c9 compile $(DEV) --libs=pip_libs --output=build my_etl.service SERVICE my_etl
    
deploy:
    chmod +x build/deploy.sh
    cd build && ./deploy.sh
    
clean:
	rm -rf pip_libs
    rm -rf build
    
.PHONY: deps build deploy clean
```

So now this will build everything and deploy it:

```shell
$ make deps build deploy
````

Of course, you can use a different build-tool if you prefer, GNU Make is not
required.

The `--dev` flag to `c9 compile` instructs the compiler to use the "development"
synthesis pipeline, which will generate IAC that targets
[localstack](https://localstack.cloud/). If you want to build for production
(currently AWS only), just omit the dev flag:

```shell
$ c9 compile --libs=pip_libs --output=prod my_etl.service SERVICE my_etl
```

Currently the AWS Region is set to eu-west-2. It'll be configurable in future.

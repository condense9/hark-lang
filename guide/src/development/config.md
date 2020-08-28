# Configuration with hark.toml

Hark is configured with a file called `hark.toml`, usually located in the
directory where the `hark` CLI is invoked (pass `--config` to use a different
file).

When you run `hark init`, `hark.toml` is created with the following default
content (values uncommented here):

```toml
## hark.toml
##
## This is where all Hark configuration takes place. Default values are
## indicated where it's appropriate to do so.
##
## Hark will work just fine without any modifications to this file, but you'll
## probably want to tweak things!

[project]

## File containing Hark code to be deployed
hark_file = "service.hk"

## Location of Python source
python_src = "src"

## Location of Hark build data
data_dir = ".hark"

## Location of Python dependencies
python_requirements = "requirements.txt"

## Path to the Python source lambda layer package (zip). If not defined, Hark
## will use pip to install requirements from python_requirements and copy source
## from python_src
package = "package.zip"

## The command to build project.package, if you have a build script
build_cmd = "./build.sh"


[instance]

## Additional AWS IAM policy statements to attach to the instance role
policy_file = <file.json>

## Extra source layers to use (maximum of 4)
## e.g., from: https://github.com/keithrozario/Klayers
extra_layers = [ ]

## Lambda function timeout (s)
lambda_timeout = 240

## Lambda function memory (MB)
lambda_memory = 128

## File with lambda environment variables
env = "hark_env.txt"

## Names of S3 buckets that `hark deploy/destroy` manages
managed_buckets = [ ]

## Names of S3 buckets to enable read/write
s3_access = [ ]

## List of S3 upload triggers. Format: [[bucket, prefix, suffix], ... ]
## Example: [["my-bucket", "images/", ".jpg"], ...]
upload_triggers = [ ]

## Enable the API Gateway trigger
enable_api = false
```



## [project]

These are project-specific configuration parameters.

Most of these don't need to be changed, except for `build_cmd` and `package`.
Hark can build Python projects that use a `requirements.txt` file to list Python
dependencies. If you use a different method, use `package` and `build_cmd` to
hook into `hark deploy`.

`package`: If defined, this will be used to locate the Lambda *layer* package -
be sure to follow the [AWS docs][1] for packaging this.

`build_cmd`: If defined, will be run before every `hark deploy`. **Note**:
`package` must also be defined in this case.


## [instance]

These are instance-specific configuration options. At the moment, Hark only
supports a single instance per project, but in the future it may support
multiple (e.g `[instance.dev]`, `[instance.prod]`).

In particular:

`env`: Set run-time environment variables here (will be copied into the Lambda
environment) in the usual ([dotenv style][2]) `VARIABLE=value` format.

`lambda_timeout` and `lambda_memory`: Control the function timeout and memory
allocation.


Hark will handle some infrastructure changes for you:

`s3_access`: Your program will be given full read/write access to S3 buckets
listed here. **Note**: must also be added to `managed_buckets`.

`upload_triggers`: Configure S3 triggering here. Usually you'll want to filter
the trigger by key prefix and suffix, which this supports. See [File
uploads](/aws/file_uploads.html).

`managed_buckets`: Hark will only modify buckets listed here.

`enable_api`: If true, an API gateway will be configured for the project. See
[HTTP APIs](/aws/http_apis.html).


[1]: https://docs.aws.amazon.com/lambda/latest/dg/python-package.html
[2]: https://www.npmjs.com/package/dotenv

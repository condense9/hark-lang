# Batch Fractal Generation

This example generates Fractals in parallel on AWS Lambda, using Python's PIL
(Pillow) library and some recursive plotting.

1. randomly generate a list of N Fractals to draw.
2. draw each one in parallel (fan-out N Lambda invocations) and save in S3.
3. Coming soon: merge them all into a collage (fan-in).

Quick-start:

```
$ echo FRACTALS_BUCKET=<your_s3_bucket> > teal_env.txt
$ teal -v deploy
$ teal invoke
```

Check out the Fractal PNGs that have been generated in your S3 bucket!

```
$ aws s3 ls s3://<your_s3_bucket>/fractals --recursive
```

---


<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [Batch Fractal Generation](#batch-fractal-generation)
    - [Prerequisites](#prerequisites)
    - [Using This Example](#using-this-example)
        - [1. Install Teal](#1-install-teal)
        - [2. Test Fractal generation locally](#2-test-fractal-generation-locally)
        - [3. Configure the deployment](#3-configure-the-deployment)
        - [4. Deploy the infrastructure](#4-deploy-the-infrastructure)
        - [5. Test it](#5-test-it)
    - [Next Steps](#next-steps)

<!-- markdown-toc end -->


## Prerequisites

To get the full experience you need:
- An AWS account and AWS CLI configured
- An S3 bucket in your account
- Python 3.8
- Minio (https://min.io/) for local testing


## Using This Example


### 1. Install Teal

```
$ pip install teal
```

Recommended: do this inside a virtual environment!


### 2. Test Fractal generation locally

Teal programs can be run locally before being deployed.

Use minio to spin up a local S3-compatible server:

```
$ mkdir -p minio_root/data

$ minio server --address 127.0.0.1:9000 minio_root
```

Check that http://127.0.0.1:9000/minio/data is working.

Point the code at the server (note that the endpoint is **http***):

```
$ export FRACTALS_BUCKET=data

$ export MINIO_ENDPOINT=http://localhost:9000
```

Run the Teal program:

```
$ teal service.tl
```

**Check the results**: Browse to http://127.0.0.1:9000/minio/data/fractals/ and
check that the fractals have been generated.


### 3. Configure the deployment

**1.** `$ echo FRACTALS_BUCKET=<your_s3_bucket> > teal_env.txt`

Variables in `teal_env.txt` will be exposed to your Python code.

**2.** Change "teal-examples-data" in `teal.toml` to the name of your S3 bucket.

Teal will be given full read/write access to this bucket.


### 4. Deploy the infrastructure

(From inside the virtual environment.)

```
$ teal deploy
```

This deploys the cloud service, according to the configuration in the "service"
part of [`teal.toml`](teal.toml).

This command does several things:
- packages the `src` directory into a lambda layer
- creates the AWS infrastructure required to run this application
- deploys the Lambda data
- deploys the Teal code

Feel free to re-run this command -- it will only update the necessary parts.

Use the `-v` flag to see what is actually updated.


### 5. Test it

```
$ teal -v invoke
```

After a little while, and if all goes well, you'll see:

```
...
START RequestId: xxx-xxx-xxx
END RequestId: xxx-xxx-xxx
REPORT RequestId: xxx-xxx-xxx 5344.70 ms	Billed Duration: 5400 ms	Memory Size: 512 MB	Max Memory Used: 86 MB	Init Duration: 481.59 ms

{'finished': True,
 'result': ['fractals/levy_c_9.png',
            'fractals/sierpinski_7.png',
            'fractals/moore_8.png'],
 'session_id': '68232w8b-6dde-4dca-ade4-23cba2b3c254',
 'vmid': 0}
['fractals/levy_c_9.png', 'fractals/sierpinski_7.png', 'fractals/moore_8.png']
Done (6s elapsed).
```

Confirm that the Fractals exist:

```
$ aws s3 ls s3://<your_s3_bucket>/fractals --recursive
```

And check the Teal logs:

```
$ teal events SESSION_ID
```

Where SESSION_ID is taken from the (verbose) output of `invoke`.

Another useful view:

```
$ teal events --unified SESSION_ID
```


## Next Steps

The pipeline could be triggered by an S3 upload (e.g. a CSV list of Fractals to
generate).

Add a final stage where all of the fractals are combined into a collage to
demonstrate fan-in.


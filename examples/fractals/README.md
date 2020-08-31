# Batch Fractal Generation 💮

[`service.hk`](service.hk) generates Fractals in parallel on AWS Lambda, using
Python's PIL (Pillow) library and some recursive plotting.

1. Randomly generate a list of N Fractals to draw.
2. Draw each one in parallel (fan-out N Lambda invocations) and save in S3.
3. Coming soon: merge them all into a collage (fan-in).

Quick-start (2-3 minutes):

```shell
$ echo FRACTALS_BUCKET=<your_s3_bucket> > hark_env.txt

$ hark -v deploy  # Set up a Hark project in your AWS account (<60s)
...

$ hark invoke  # Start the computation on Lambda
['fractals/rings_8.png', 'fractals/hilbert2_6.png', 'fractals/levy_c_5.png']

$ hark destroy  # Tear down the infrastructure (<60s)
Done.
```

Check out the Fractal PNGs that have been generated in your S3 bucket!

```shell
$ aws s3 ls s3://<your_s3_bucket>/fractals --recursive
2020-06-08 13:19:39      28695 fractals/hilbert2_6.png
2020-06-08 13:19:38      29558 fractals/levy_c_5.png
2020-06-08 13:19:38       7451 fractals/rings_8.png
```

![Sierpinski](img/sierpinski.png)

---

(Expected time to complete: <5 minutes)

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [Batch Fractal Generation 💮](#batch-fractal-generation-💮)
    - [Prerequisites](#prerequisites)
    - [Walkthrough](#walkthrough)
        - [1. Install Hark](#1-install-hark)
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


## Walkthrough


### 1. Install Hark

```shell
$ pip install hark
```

Recommended: do this inside a virtual environment!


### 2. Test Fractal generation locally

Use minio to spin up a local S3-compatible server:

```shell
$ mkdir -p minio_root/data

$ minio server --address 127.0.0.1:9000 minio_root
```

Check that http://127.0.0.1:9000/minio/data is working.

Point the code at the server (note that the endpoint is **http**):

```shell
$ export FRACTALS_BUCKET=data

$ export MINIO_ENDPOINT=http://127.0.0.1:9000
```

Generate fractals:

```shell
$ hark service.hk
```

**Check the results**: Browse to http://127.0.0.1:9000/minio/data/fractals/ and
check that the fractals have been generated.


### 3. Configure the deployment

**1.** `$ echo FRACTALS_BUCKET=<your_s3_bucket> > hark_env.txt`

Variables in `hark_env.txt` will be exposed to your Python code on AWS.

**2.** Change "hark-examples-data" in `hark.toml` to the name of your S3 bucket.
*Important:* there are two places this need to be changed!

Your code will be given full read/write access to this bucket.


### 4. Deploy the infrastructure

```shell
$ hark deploy
```

This deploys the cloud service according to the configuration in the `[service]`
section of [`hark.toml`](hark.toml). Use `hark destroy` to reverse it.

This command does several things:
- packages the `src` directory into a lambda layer
- creates the AWS infrastructure required to run this application
- deploys the Lambda data
- deploys the Hark code

Feel free to re-run this command -- it's idempotent.

Use the `-v` flag to see what is actually updated.


### 5. Test it

```shell
$ hark -v invoke
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

```shell
$ aws s3 ls s3://<your_s3_bucket>/fractals --recursive
# ...
```

Check the standard output, where `$SESSION_ID` is taken from the (verbose)
output of `invoke` (`68232w8b-6dde-4dca-ade4-23cba2b3c254` in this case):

```shell
$ hark logs $SESSION_ID
['crystal', 16]
['tiles', 18]
['crystal', 14]
uploading /tmp/tiles_18.png to s3.Bucket(name='hark-examples-data')...
uploading /tmp/crystal_16.png to s3.Bucket(name='hark-examples-data')...
uploading /tmp/crystal_14.png to s3.Bucket(name='hark-examples-data')...
Done

Done (1s elapsed).
```

And an execution trace (more detail coming soon):

```shell
$ hark events $SESSION_ID
Thread 0:
0.000  run
0.000  call {'fn_name': '<TlForeignPtr src.draw.random_fractals>'}
0.000  call {'fn_name': '<TlFunctionPtr #2:map_wait>'}
0.000  call {'fn_name': '<TlFunctionPtr #1:map>'}
0.001  call {'fn_name': '<TlFunctionPtr #0:map_tr>'}
0.001  call {'fn_name': 'nullp'}
0.001  call {'fn_name': 'rest'}
0.001  call {'fn_name': 'first'}
0.001  call {'fn_name': '<TlFunctionPtr #4:build_fractal_async>'}
0.269  return
0.269  call {'fn_name': 'append'}
0.269  call {'fn_name': 'nullp'}
0.269  call {'fn_name': 'rest'}
0.269  call {'fn_name': 'first'}
0.269  call {'fn_name': '<TlFunctionPtr #4:build_fractal_async>'}
0.370  return
0.370  call {'fn_name': 'append'}
0.370  call {'fn_name': 'nullp'}
0.370  call {'fn_name': 'rest'}
0.370  call {'fn_name': 'first'}
0.370  call {'fn_name': '<TlFunctionPtr #4:build_fractal_async>'}
0.466  return
0.466  call {'fn_name': 'append'}
0.467  call {'fn_name': 'nullp'}
0.467  return
0.467  return
0.467  call {'fn_name': '<TlFunctionPtr #1:map>'}
0.467  call {'fn_name': '<TlFunctionPtr #0:map_tr>'}
0.467  call {'fn_name': 'nullp'}
0.467  call {'fn_name': 'rest'}
0.467  call {'fn_name': 'first'}
0.467  call {'fn_name': 'wait'}
0.520  stop
2.892  run
2.892  call {'fn_name': 'append'}
2.893  call {'fn_name': 'nullp'}
2.893  call {'fn_name': 'rest'}
2.893  call {'fn_name': 'first'}
2.893  call {'fn_name': 'wait'}
3.083  call {'fn_name': 'append'}
3.084  call {'fn_name': 'nullp'}
3.084  call {'fn_name': 'rest'}
3.084  call {'fn_name': 'first'}
3.084  call {'fn_name': 'wait'}
3.192  call {'fn_name': 'append'}
3.192  call {'fn_name': 'nullp'}
3.192  return
3.192  return
3.192  return
3.192  call {'fn_name': 'print'}
3.427  stop
Thread 1:
0.737  run
0.737  call {'fn_name': 'print'}
0.924  call {'fn_name': 'nth'}
0.925  call {'fn_name': 'nth'}
0.925  call {'fn_name': '<TlForeignPtr src.draw.save_fractal_to_file>'}
1.915  call {'fn_name': '<TlForeignPtr src.store.upload_to_bucket>'}
2.826  stop
Thread 2:
0.452  run
0.452  call {'fn_name': 'print'}
0.718  call {'fn_name': 'nth'}
0.718  call {'fn_name': 'nth'}
0.718  call {'fn_name': '<TlForeignPtr src.draw.save_fractal_to_file>'}
1.683  call {'fn_name': '<TlForeignPtr src.store.upload_to_bucket>'}
2.063  stop
Thread 3:
0.536  run
0.536  call {'fn_name': 'print'}
0.804  call {'fn_name': 'nth'}
0.804  call {'fn_name': 'nth'}
0.804  call {'fn_name': '<TlForeignPtr src.draw.save_fractal_to_file>'}
1.637  call {'fn_name': '<TlForeignPtr src.store.upload_to_bucket>'}
2.325  stop
Done (0s elapsed).
```

Another useful view, highlighting the parallel execution of the threads:

```shell
$ hark events --unified $SESSION_ID
    Time  Thread  Event
   0.000     0     run
   0.000     0     call {'fn_name': '<TlForeignPtr src.draw.random_fractals>'}
   0.000     0     call {'fn_name': '<TlFunctionPtr #2:map_wait>'}
   0.000     0     call {'fn_name': '<TlFunctionPtr #1:map>'}
   0.001     0     call {'fn_name': '<TlFunctionPtr #0:map_tr>'}
   0.001     0     call {'fn_name': 'nullp'}
   0.001     0     call {'fn_name': 'rest'}
   0.001     0     call {'fn_name': 'first'}
   0.001     0     call {'fn_name': '<TlFunctionPtr #4:build_fractal_async>'}
   0.269     0     return
   0.269     0     call {'fn_name': 'append'}
   0.269     0     call {'fn_name': 'nullp'}
   0.269     0     call {'fn_name': 'rest'}
   0.269     0     call {'fn_name': 'first'}
   0.269     0     call {'fn_name': '<TlFunctionPtr #4:build_fractal_async>'}
   0.370     0     return
   0.370     0     call {'fn_name': 'append'}
   0.370     0     call {'fn_name': 'nullp'}
   0.370     0     call {'fn_name': 'rest'}
   0.370     0     call {'fn_name': 'first'}
   0.370     0     call {'fn_name': '<TlFunctionPtr #4:build_fractal_async>'}
   0.452     2     run
   0.452     2     call {'fn_name': 'print'}
   0.466     0     return
   0.466     0     call {'fn_name': 'append'}
   0.467     0     call {'fn_name': 'nullp'}
   0.467     0     return
   0.467     0     return
   0.467     0     call {'fn_name': '<TlFunctionPtr #1:map>'}
   0.467     0     call {'fn_name': '<TlFunctionPtr #0:map_tr>'}
   0.467     0     call {'fn_name': 'nullp'}
   0.467     0     call {'fn_name': 'rest'}
   0.467     0     call {'fn_name': 'first'}
   0.467     0     call {'fn_name': 'wait'}
   0.520     0     stop
   0.536     3     run
   0.536     3     call {'fn_name': 'print'}
   0.718     2     call {'fn_name': 'nth'}
   0.718     2     call {'fn_name': 'nth'}
   0.718     2     call {'fn_name': '<TlForeignPtr src.draw.save_fractal_to_file>'}
   0.737     1     run
   0.737     1     call {'fn_name': 'print'}
   0.804     3     call {'fn_name': 'nth'}
   0.804     3     call {'fn_name': 'nth'}
   0.804     3     call {'fn_name': '<TlForeignPtr src.draw.save_fractal_to_file>'}
   0.924     1     call {'fn_name': 'nth'}
   0.925     1     call {'fn_name': 'nth'}
   0.925     1     call {'fn_name': '<TlForeignPtr src.draw.save_fractal_to_file>'}
   1.637     3     call {'fn_name': '<TlForeignPtr src.store.upload_to_bucket>'}
   1.683     2     call {'fn_name': '<TlForeignPtr src.store.upload_to_bucket>'}
   1.915     1     call {'fn_name': '<TlForeignPtr src.store.upload_to_bucket>'}
   2.063     2     stop
   2.325     3     stop
   2.826     1     stop
   2.892     0     run
   2.892     0     call {'fn_name': 'append'}
   2.893     0     call {'fn_name': 'nullp'}
   2.893     0     call {'fn_name': 'rest'}
   2.893     0     call {'fn_name': 'first'}
   2.893     0     call {'fn_name': 'wait'}
   3.083     0     call {'fn_name': 'append'}
   3.084     0     call {'fn_name': 'nullp'}
   3.084     0     call {'fn_name': 'rest'}
   3.084     0     call {'fn_name': 'first'}
   3.084     0     call {'fn_name': 'wait'}
   3.192     0     call {'fn_name': 'append'}
   3.192     0     call {'fn_name': 'nullp'}
   3.192     0     return
   3.192     0     return
   3.192     0     return
   3.192     0     call {'fn_name': 'print'}
   3.427     0     stop
Done (0s elapsed).
```


## Next Steps

The pipeline could be triggered by an S3 upload (e.g. a CSV list of Fractals to
generate).

Add a final stage where all of the fractals are combined into a collage to
demonstrate fan-in.


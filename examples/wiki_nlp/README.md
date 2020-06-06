# Wikipedia NLP

Batch NLP (natural language processing) analysis of wikipedia data dumps. 

TODO - is this below the AWS free tier?

TODO describe workflow.

Workflow:
- read CSV of fractals to generate
- generate all of them in parallel
- assemble into a collage


<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [Wikipedia NLP](#wikipedia-nlp)
    - [Prerequisites](#prerequisites)
    - [Using This Example](#using-this-example)
        - [1. Install Teal](#1-install-teal)
        - [2. Test it locally](#2-test-it-locally)
        - [3. Deploy the infrastructure](#3-deploy-the-infrastructure)
        - [4. Test it](#4-test-it)
        - [5. To production (optional)](#5-to-production-optional)
    - [Next Steps](#next-steps)

<!-- markdown-toc end -->


## Prerequisites

To try this example you need:
- An AWS account and AWS CLI configured
- Python 3.8
- Minio (https://min.io/) for local testing


## Using This Example


### 1. Install Teal and retrieve Wikipedia data

`pip install teal`

Recommended: do this inside a virtual environment!

Next, download the large (~800MB) archive of wikipedia abstracts into a
directory we'll use with minio later.

```
mkdir -p minio_root/wikipedia_data

curl https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract.xml.gz \
  -O minio_root/wikipedia_data/enwiki-latest-abstract.xml.gz
```


### 2. Test it locally

Teal programs can be run locally before being deployed.

Use minio to spin up a local S3-compatible server:

`minio server --address 127.0.0.1:9000 minio_root`

Check that http://127.0.0.1:9000/minio/wikipedia_data/ shows the data.

Point the code at the server (note that the endpoint is **http***):

```
export S3_BUCKET=wikipedia_data

export MINIO_ENDPOINT=http://localhost:9000
```

And run the Teal program:

`teal main.tl enwiki-latest-abstract.xml.gz`

Check the results: TODO


### 3. Deploy the infrastructure

(From inside the virtual environment.)

`teal deploy`

This deploys the cloud service, according to the configuration in the "service"
part of [`teal.toml`](teal.toml). 

This command does several things:
- packages the `src` directory into a lambda layer
- creates the AWS infrastructure required to run this application
- deploys the Lambda data
- deploys the Teal code

Feel free to re-run this command -- it will only update the necessary parts.


### 4. Test it

Upload the test data to S3:

`s3 cp TODO`

Trigger the function:

`teal invoke TODO`

And monitor:

- `teal status` ?? to implement
- `teal list` ?? to implement
- `teal logs SESSION_ID`


## Next Steps

The pipeline could be triggered by an S3 upload.

TODO - add a config option (s3_trigger)? Or make it manual

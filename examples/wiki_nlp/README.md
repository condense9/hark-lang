# Wikipedia NLP

Batch NLP (natural language processing) analysis of wikipedia data dumps. 

TODO - is this below the AWS free tier?

TODO describe workflow.

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
- Serverless framework (https://serverless.com/)
- Python 3.8


## Using This Example


### 1. Install Teal

`pip install teal`

Recommended: do this inside a virtual environment!


### 2. Test it locally

Teal programs can be run locally before being deployed.

Use minio to spin up a local S3-compatible server:

`minio TODO`

Copy some test data into the bucket:

`s3 cp TODO --endpoint-url`

Point the code at the server:

`export S3_URL https://localhost:TODO`

And run the Teal program:

`teal main.tl -f on_upload test_data.xml`

Check the results: TODO


### 3. Deploy the infrastructure

(From inside the virtual environment.)

`teal deploy`

This deploys the cloud service, according to the configuration in the "service"
part of [`teal.toml`](teal.toml). Feel free to re-run this command -- it will
only update the necessary parts.

This command does several things:
- package the `src` directory into a lambda layer
- 


### 4. Test it

Upload the test data to S3:

`s3 cp TODO`

Trigger the function:

`tealc run on_upload test_data.xml`

And monitor:

- `tealc status` ?? (Teal Cloud)
- `tealc list`
- `tealc logs [-f] SESSION_ID`


### 5. To production (optional)

`serverless deploy --prod`

`teal deploy`


## Next Steps

The pipeline could be triggered by an S3 upload.

TODO - add serverless.yml extension to do this.

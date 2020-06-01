# Wikipedia NLP

Batch NLP (natural language processing) analysis of wikipedia data dumps. 

TODO - is this below the AWS free tier?

TODO describe workflow.


## Getting Started

How to deploy this on your infrastructure.

Requirements:
- An AWS account and AWS CLI configured
- Serverless framework (https://serverless.com/)
- Python 3.8


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


### 3. Get Teal deployment package

(From inside the virtual environment.)

`teal pkg --dev`

This builds and saves the latest Teal deployment package as `teal_lambda.zip`.

In future you might be able to do `teal pkg --version X` to get a specific
version of Teal, or ommit the `--version` flag to just download the latest
version. Not implemented yet.



### 4. Build source deployment package

`./make_src_layer.sh`

This packages `src` and its dependencies (in `requirements.txt`) into a Lambda
layer package.


### 5. Deploy the infrastructure

`serverless deploy`


`serverless outputs`

This 


### 6. Test it

Upload the test data to S3:

`s3 cp TODO`

Trigger the function:

`tealc run on_upload test_data.xml`

And monitor:

`tealc status` ?? (Teal Cloud)
`tealc list`
`tealc logs [-f] SESSION_ID`


### 7. To production (optional)

`serverless deploy --prod`

`teal deploy`


## Further Improvements

The pipeline could be triggered by an S3 upload.

TODO - add serverless.yml extension to do this.

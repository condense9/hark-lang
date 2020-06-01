# Wikipedia NLP

Batch NLP (natural language processing) analysis of wikipedia data dumps. 

TODO - is this below the AWS free tier?

## Getting Started

How to deploy this on your infrastructure.

Requirements:
- An AWS account and AWS CLI configured
- Serverless framework (https://serverless.com/)
- Python 3.8

### 1. Install Teal

`pip install teal`

Recommended: do this inside a virtual environment!

### 2. Get Teal deployment package

(From inside the virtual environment.)

`teal pkg --dev`

This builds and saves the latest Teal deployment package as `teal_lambda.zip`.

In future you might be able to do `teal pkg --version X` to get a specific
version of Teal, or ommit the `--version` flag to just download the latest
version. Not implemented yet.


### 3. Build source deployment package

`./make_src_layer.sh`

This packages `src` and its dependencies (in `requirements.txt`) into a Lambda
layer package.


### 4. Deploy the infrastructure

`serverless deploy`


`serverless outputs`

This 


### 5. To production

`serverless deploy --prod`

`teal deploy`



## Further Improvements

The pipeline could be triggered by an S3 upload.

TODO - add serverless.yml extension to do this.

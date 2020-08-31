# Hark Integration Tests

All user-level testing.

Pre-requisites:
- Docker
- An AWS Account & user to run tests (see below)


## AWS Account Setup

These tests have to be run with a real AWS account, because the localstack
community version doesn't support Lambda Layers.

The recommended approach is to create a new IAM user for running these tests,
and assign the IAM permissions listed in `./test_user_policy.json`. The process
to do that is described here.

**Don't use an account with production data in it!**


### Step 1: Create an IAM user

1. Go to [https://console.aws.amazon.com/iam/home][1], select "Users" under
**Access Management**, and hit "Add user".

2. Under **Access Type**, select "Programmatic access" *only*.

3. In **Set Permissions**, select "Attach existing policies directly", and hit
"Create policy".

4. In the New Policy tab, select JSON, and copy in the contents of
[test_user_policy.json](./test_user_policy.json).

5. Back in the Add User tab, select the policy you've just created.

6. Finish the new user creation process and save the `ACCESS_KEY_ID` and
`SECRET_ACCESS_KEY` for step 2.


### Step 2: Set environment variables

The test harness uses AWS credentials stored in `stories/.env`.

`stories/.env` needs the following variables. Fill in the access key blanks with
the details from your user in step 1.

```
AWS_DEFAULT_REGION=eu-west-2
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```


## Test Stories

Tests are grouped into user stories (start-to-finish journey of a Hark user
accomplishing something).

Each test story has a `test.sh` file which defines the user actions, and a
`Dockerfile` which defines the environment image.

For each story, run one of:
- `make test` to test the latest PyPI version of Hark
- `HARK_VERSION="==x.x.x" make test` for a specific PyPI version (note the "=="
  prefix!)
- `make local` to test the current Hark checkout
- `make local-nobuild` to test the current Hark checkout without rebuilding it
  (e.g. if only `test.sh` has changed)


If you don't have `make` installed, or don't like using Make, grab the commands
in [stories/common.mk](stories/common.mk) and call them directly.


### Story: Getting Started

Runs the 2 minute getting-started tutorial in [../README.md](../README.md).


### Story: Try Fractals

Runs the [fractals example](../examples/fractals). **Note**: You must add a
definition for `FRACTALS_BUCKET` (an S3 bucket in your account) to
`stories/.env` before running this. The test will write some data to the bucket,
and it doesn't clean up after itself :(.

To create a bucket for this purpose, run:

```shell
aws s3 mb s3://bucket-name
```

You can (forcefully) delete the bucket with:

```shell
aws s3 rb s3://bucket-name --force
```


## Troubleshooting

A common failure mode is that botocore throws a `KMSAccessDeniedException`
exception which [appears to be related][2] to quickly deleting and recreating
IAM roles with the same name. In the worst case, a test will fail, and you'll be
left with a Hark instance in your account.

In either case, the easiest fix is to just destroy the whole instance and start
again.

To do that, run `hark destroy --uuid $UUID` where `$UUID` is the UUID of the
instance created in the test (this should be shown the test logs).

To investigate issues, it's often enough to run `hark stdout --uuid $UUID $SID`
where `$SID` is the session ID that failed (again, check the logs).

[1]: https://console.aws.amazon.com/iam/home
[2]: https://github.com/serverless/examples/issues/279

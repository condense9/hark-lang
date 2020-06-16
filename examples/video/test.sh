#!/usr/bin/env bash

echo fake > fake.mp4

aws s3 rm s3://teal-examples-data/fake.mp4
aws s3 cp fake.mp4 s3://teal-examples-data/

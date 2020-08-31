#!/usr/bin/env bash

echo fake > fake.mp4

aws s3 rm s3://hark-examples-data/fake.mp4
aws s3 cp fake.mp4 s3://hark-examples-data/

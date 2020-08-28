# Video Processing

Status: WIP. The Python tasks are still placeholders.

When a video file is uploaded, [`video.hk`](video.hk) transcodes it into several
different formats and sizes as quickly as possible on AWS Lambda.

1. Download the file
2. Check the format is suitable.
3. Start a new thread for each transcoding task.
4. When each task finishes, save the results.


```shell
aws s3 cp foo.txt s3://hark-examples-data/
```

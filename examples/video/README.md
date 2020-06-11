# Video Processing

When a video file is uploaded, [`video.tl`'](video.tl) transcode it into several
different formats and sizes as quickly as possible on AWS Lambda.

1. Download the file
2. Check the format is suitable.
3. Start a new thread for each transcoding task.
4. When each task finishes, save the results.

/** -*- mode: rust -*-  (it's not rust, but the syntax is close)
 * video.tl
 *
 * Transcode video files uploaded to an S3 bucket.
 *
 * Optimise for time by performing each transcoding task in its own thread.
**/

import(transcode, :python src.video)
import(correct_format, :python src.video)
import(save_results, :python src.store)

// Teal standard library functions to get/put files in S3
import(s3_get, teal.aws)
import(s3_put, teal.aws)


/**
 * The main transcode task
**/
fn transcode_and_save(bucket, key, format, size) {
  filename = s3_get(bucket, key)
  result = transcode(filename, format, size)

  if result {
    save_results(result)
  }
  else {
    error("transcoding failed")
  }
}


/**
 * The upload handler - check the format and spin up transcode tasks
**/
#[aws_trigger="s3", bucket="upload-bucket"]
fn on_upload(bucket, key) {
  filename = s3_get(bucket, key)

  if correct_format(filename) {
    mp4 = async transcode_and_save(bucket, key, "mp4", "TODO")
    mp4_2 = async transcode_and_save(bucket, key, "mp4", "TODO")
    hls = async transcode_and_save(bucket, key, "hls", "TODO")
  }
  else {
    error("bad format")
  }
}

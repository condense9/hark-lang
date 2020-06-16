/** -*- mode: javascript -*-  (it's not, but the syntax is close)
 * video.tl
 *
 * Transcode video files uploaded to an S3 bucket.
 *
 * Optimise for time by performing each transcoding task in its own thread.
**/

import(transcode, :python src.video)
import(correct_format, :python src.video)
import(save_results, :python src.video)


// Will be part of the std lib
fn error(message) {
  signal("error", message)
}


/**
 * The main transcode task
**/
fn transcode_and_save(bucket, key, format, size) {
  result = transcode(bucket, key, format, size)

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
// #[aws_trigger="s3", bucket="upload-bucket"]
fn on_upload(bucket, key) {
  if correct_format(bucket, key) {
    print("Format ok.")
    mp4 = async transcode_and_save(bucket, key, "mp4", "1080p")
    mp4_2 = async transcode_and_save(bucket, key, "mp4", "720p")
    hls = async transcode_and_save(bucket, key, "hls", "480")

    await mp4
    await mp4_2
    await hls

    "done."
  }
  else {
    error("bad format")
  }
}

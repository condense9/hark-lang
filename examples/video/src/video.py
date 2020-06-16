"""Video processing routines"""
import random
import time


def transcode(bucket, key, video_format, size):
    print("Transcoding {key} -> {video_format} ({size})")

    # .... Do stuff.
    time.sleep(5)

    # occasionally, fail
    if random.random() < 0.2:
        return None
    else:
        return [key, "ok"]


def correct_format(bucket, key) -> bool:
    print(f"Checking format of {key}...")

    # occasionally, fail
    if random.random() < 0.2:
        return False
    else:
        return True


def save_results(results) -> bool:
    print("Saving results:", results)
    time.sleep(2)
    return True

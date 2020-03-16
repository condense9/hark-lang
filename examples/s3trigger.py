# Foundation: named futures.
# No branching...


@Program
def main(infile: FileIO):
    save_metadata(infile)
    Map()


def _init():
    backend.on(bucket, main)


if __name__ == "__main__":
    _init()

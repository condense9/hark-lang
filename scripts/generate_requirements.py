import os
import json

__dir__ = os.path.dirname(os.path.realpath(__file__))


def read_json_file(path):
    with open(path) as f:
        return json.load(f)


def main():
    root = read_json_file(os.path.join(__dir__, "Pipfile.lock"))

    for name, pkg in root["default"].items():
        version = pkg["version"]
        hashes = " ".join([f"--hash={t}" for i, t in enumerate(pkg["hashes"])])
        print(f"{name}{version} {hashes}")


if __name__ == "__main__":
    main()

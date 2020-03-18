import os
import json

__dir__ = os.path.dirname(os.path.realpath(__file__))


def read_json_file(path):
    with open(path) as f:
        return json.load(f)


def main():
    root = read_json_file(os.path.join(__dir__, 'Pipfile.lock'))

    for name, pkg in root["default"].items():
        version = pkg["version"]
        sep = lambda i: "" if i == len(pkg["hashes"]) - 1 else " \\"
        hashes = [f'--hash={t}{sep(i)}' for i, t in enumerate(pkg["hashes"])]
        tail = '' if len(hashes) == 0 else f' {hashes[0]}'
        print(f'{name} {version}{tail}')
        for h in hashes[1:]:
            print(f'    {h}')


if __name__ == "__main__":
    main()

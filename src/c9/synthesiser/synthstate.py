"""Hold state in the synthesis pipeline"""

from os.path import join


class SynthState:
    def __init__(self, resources: set, iac, deploy_commands, api_code_dir):
        self.api_code_dir = api_code_dir  # a bit ugly - only needed for functions atm
        self.resources = resources
        self.iac = iac
        self.deploy_commands = deploy_commands
        self.api_code_dir = api_code_dir

    def filter_resources(self, rtype) -> set:
        return set(r for r in self.resources if isinstance(r, rtype))

    def gen_iac(self, path):
        """Write the IAC to files in path"""
        for generator in self.iac:
            with open(join(path, generator.filename), "w") as f:
                f.write(generator.generate())
                f.write("\n")

        with open(join(path, "deploy.sh"), "w") as f:
            f.write("#!/usr/bin/env bash\n")
            f.write("set -xe\n")
            f.write("\n".join(self.deploy_commands))

    def show(self):
        print("Resources:", self.resources)
        print("IAC:", self.iac)
        print("Deploy:", self.deploy_commands)

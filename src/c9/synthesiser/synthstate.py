"""Hold state in the synthesis pipeline"""

import os
from os.path import join


class SynthState:
    def __init__(self, name, resources: set, iac, deploy_commands):
        self.service_name = name.replace(" ", "-")
        self.resources = set(resources)
        self.iac = iac
        self.deploy_commands = deploy_commands

    def filter_resources(self, rtype) -> set:
        return [r for r in self.resources if isinstance(r, rtype)]

    def gen_iac(self, path):
        """Write the IAC to files in path"""
        for generator in self.iac:
            generator.generate(path)

        with open(join(path, "deploy.sh"), "w") as f:
            f.write("#!/usr/bin/env bash\n")
            f.write("set -xe\n")
            f.write("\n".join(self.deploy_commands))

    def show(self):
        print("Resources:", self.resources)
        print("IAC:", self.iac)
        print("Deploy:", self.deploy_commands)

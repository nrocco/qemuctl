import click
import os
import yaml

from qemu.hypervisor import Hypervisor


def read_config(ctx, param, value):
    if not value:
        return
    if not isinstance(value, list):
        value = [value]
    for file in value:
        file = os.path.expanduser(file)
        if not os.path.exists(file):
            continue
        with open(file) as config_file:
            ctx.default_map = yaml.safe_load(config_file)
            return


pass_hypervisor = click.make_pass_decorator(Hypervisor)

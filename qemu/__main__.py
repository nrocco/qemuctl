import click
import logging
import os
import yaml

from . import __version__
from .hypervisor import Hypervisor
from .models import Plan


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


@click.group(context_settings=dict(auto_envvar_prefix="QEMU", show_default=True))
@click.option("--config", default=[".qemuctl.yaml", "~/.qemuctl.yaml", "/etc/qemuctl.yaml"], help="Location to a config file", is_eager=True, callback=read_config)
@click.option("--hypervisor", help="Hypervisor endpoint")
@click.option("--state-directory", default="/var/lib/qemu", help="Directory on the hypervisor where all state is stored")
@click.option("--vnc-address", default="127.0.0.1", help="Address for VNC monitors")
@click.option("--vnc-password", default="changeme", help="Default VNC password")
@click.option("-v", "--verbose", count=True, help="Verbose logging, repeat to increase verbosity")
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, verbose, config, hypervisor, state_directory, vnc_address, vnc_password):
    """
    Manage virtual machines using qemu
    """
    logging.basicConfig(level=max(30 - verbose * 10, 10), format='[%(asctime)-15s] [%(levelname)s] %(message)s')
    ctx.meta['hypervisor'] = Hypervisor(hypervisor, state_directory, vnc_address, vnc_password)
    with open("Qemufile", "r") as file:
        ctx.meta['plan'] = Plan(yaml.safe_load(file), ctx.meta['hypervisor'])


@main.command()
@click.option('--dry-run/--no-dry-run', default=False, help="Do not create vms")
@click.argument('vms', nargs=-1)
@click.pass_context
def create(ctx, dry_run, vms):
    """
    Create vms
    """
    for vm in ctx.meta['plan'].vms:
        if vms and vm.name not in vms:
            continue
        if dry_run:
            print(' '.join(vm.as_qemu_command(ctx.find_root().params['state_directory'])))
            return
        vm.create()
        print("{} created".format(vm.name))


@main.command()
@click.argument('vms', nargs=-1)
@click.pass_context
def start(ctx, vms):
    """
    Start vms
    """
    for vm in ctx.meta['plan'].vms:
        if vms and vm.name not in vms:
            continue
        vm.start()
        print("{} started".format(vm.name))


@main.command()
@click.argument('vms', nargs=-1)
@click.pass_context
def restart(ctx, vms):
    """
    Restart vms
    """
    for vm in ctx.meta['plan'].vms:
        if vms and vm.name not in vms:
            continue
        vm.restart()
        print("{} restarted".format(vm.name))


@main.command()
@click.argument('vms', nargs=-1)
@click.pass_context
def stop(ctx, vms):
    """
    Stop vms
    """
    for vm in ctx.meta['plan'].vms:
        if vms and vm.name not in vms:
            continue
        vm.stop()
        print("{} stopped".format(vm.name))


@main.command()
@click.argument('vms', nargs=-1)
@click.pass_context
def destroy(ctx, vms):
    """
    Destroy vms and their state
    """
    for vm in ctx.meta['plan'].vms:
        if vms and vm.name not in vms:
            continue
        vm.destroy()
        print("{} destroyed".format(vm.name))


@main.command()
@click.argument('vms', nargs=-1)
@click.pass_context
def info(ctx, vms):
    """
    Get information about vms
    """
    print("Plan:")
    print("  Vms:")
    for vm in ctx.meta['plan'].vms:
        if vms and vm.name not in vms:
            continue
        info = vm.info()
        print("    {}:".format(vm.name))
        print("      Status: {status}".format(**info))
        print("      Display: {display}".format(**info))


if __name__ == "__main__":
    main()

import click
import logging
import os
import yaml

from . import __version__
from .models import Plan
from .ssh import Qmp
from .ssh import Ssh


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


pass_plan = click.make_pass_decorator(Plan)


@click.group(context_settings=dict(auto_envvar_prefix="QEMU", show_default=True))
@click.option("--config", default=[".qemuctl.yaml", "~/.qemuctl.yaml", "/etc/qemuctl.yaml"], help="Location to a config file", is_eager=True, callback=read_config)
@click.option("--hypervisor")
@click.option("--state-directory", default="/var/lib/qemu")
@click.option("--vnc-address", default="127.0.0.1")
@click.option("--vnc-password", default="changeme")
@click.option("-v", "--verbose", count=True)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, verbose, config, hypervisor, state_directory, vnc_address, vnc_password):
    """
    Manage virtual machines using qemu
    """
    logging.basicConfig(level=max(30 - verbose * 10, 10), format='[%(asctime)-15s] [%(levelname)s] %(message)s')
    with open("Qemufile", "r") as file:
        ctx.obj = Plan(yaml.safe_load(file))


@main.command()
@click.option('--dry-run/--no-dry-run', default=False)
@click.argument('vms', nargs=-1)
@pass_plan
@click.pass_context
def create(ctx, plan, dry_run, vms):
    """
    Create vms
    """
    for vm in plan.vms:
        if vms and vm.name not in vms:
            continue
        if dry_run:
            print(' '.join(vm.qemu_command(ctx.find_root().params['state_directory'])))
        else:
            Ssh(ctx.find_root().params['hypervisor'], vm.qemu_command(ctx.find_root().params['state_directory'], ctx.find_root().params['vnc_address']))
            with Qmp(ctx.find_root().params['hypervisor'], os.path.join(ctx.find_root().params['state_directory'], vm.name, "qmp.sock")) as qmp:
                qmp.execute("change-vnc-password", password=ctx.find_root().params['vnc_password'])
                response = qmp.execute("query-vnc")
                print("{}".format(vm.name))
                print("  Display: vnc://:{vnc_password}@{host}:{service}".format(**response, vnc_password=ctx.find_root().params['vnc_password']))
                qmp.execute("cont")
            logging.info("{} created".format(vm))


@main.command()
@click.argument('vms', nargs=-1)
@pass_plan
@click.pass_context
def start(ctx, plan, vms):
    """
    Start vms
    """
    for vm in plan.vms:
        if vms and vm.name not in vms:
            continue
        with Qmp(ctx.find_root().params['hypervisor'], os.path.join(ctx.find_root().params['state_directory'], vm.name, "qmp.sock")) as qmp:
            qmp.execute("cont")
        logging.info("{} started".format(vm))


@main.command()
@click.argument('vms', nargs=-1)
@pass_plan
@click.pass_context
def restart(ctx, plan, vms):
    """
    Restart vms
    """
    for vm in plan.vms:
        if vms and vm.name not in vms:
            continue
        with Qmp(ctx.find_root().params['hypervisor'], os.path.join(ctx.find_root().params['state_directory'], vm.name, "qmp.sock")) as qmp:
            qmp.execute("system_reset")
        logging.info("{} restarted".format(vm))


@main.command()
@click.argument('vms', nargs=-1)
@pass_plan
@click.pass_context
def stop(ctx, plan, vms):
    """
    Stop vms
    """
    for vm in plan.vms:
        if vms and vm.name not in vms:
            continue
        with Qmp(ctx.find_root().params['hypervisor'], os.path.join(ctx.find_root().params['state_directory'], vm.name, "qmp.sock")) as qmp:
            qmp.execute("stop")
        logging.info("{} stopped".format(vm))


@main.command()
@click.argument('vms', nargs=-1)
@pass_plan
@click.pass_context
def destroy(ctx, plan, vms):
    """
    Destroy vms and their state
    """
    for vm in plan.vms:
        if vms and vm.name not in vms:
            continue
        with Qmp(ctx.find_root().params['hypervisor'], os.path.join(ctx.find_root().params['state_directory'], vm.name, "qmp.sock")) as qmp:
            qmp.execute("quit")
        # TODO destroy entire folder with state
        logging.info("{} destroyed".format(vm))


@main.command()
@click.argument('vms', nargs=-1)
@pass_plan
@click.pass_context
def info(ctx, plan, vms):
    """
    Get information about vms
    """
    print("Plan:")
    print("  Vms:")
    for vm in plan.vms:
        if vms and vm.name not in vms:
            continue
        print("    {}:".format(vm.name))
        with Qmp(ctx.find_root().params['hypervisor'], os.path.join(ctx.find_root().params['state_directory'], vm.name, "qmp.sock")) as qmp:
            response = qmp.execute("query-status")
            print("      Status: {status}".format(**response))
            response = qmp.execute("query-vnc")
            print("      Display: vnc://:{vnc_password}@{host}:{service}".format(**response, vnc_password=ctx.find_root().params['vnc_password']))


if __name__ == "__main__":
    main()

import click
import logging

from qemu import __version__
from qemu.hypervisor import Hypervisor

from .images import images
from .networks import networks
from .vms import vms
from .utils import read_config


@click.group(context_settings=dict(auto_envvar_prefix="QEMU", show_default=True))
@click.option("--config", default=[".qemuctl.json", "~/.qemuctl.json", "/etc/qemuctl.json"], help="Location to a config file", is_eager=True, callback=read_config)
@click.option("--hypervisor", help="Hypervisor endpoint")
@click.option("--state-directory", default="/var/lib/qemu", help="Directory on the hypervisor where all state is stored")
@click.option("--vnc-address", default="127.0.0.1", help="Address for VNC monitors")
@click.option("--vnc-password", default="changeme", help="Default VNC password")
@click.option("-v", "--verbose", count=True, help="Verbose logging, repeat to increase verbosity")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, verbose, config, hypervisor, state_directory, vnc_address, vnc_password):
    """
    Manage virtual machines using qemu
    """
    logging.basicConfig(level=max(30 - verbose * 10, 10), format="[%(asctime)-15s] [%(levelname)s] %(message)s")
    ctx.obj = Hypervisor(hypervisor, state_directory, vnc_address, vnc_password)


cli.add_command(images)
cli.add_command(networks)
cli.add_command(vms)

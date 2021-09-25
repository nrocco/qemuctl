import click
import json
import logging
import math
import os
import subprocess

from qemu import __version__
from requests import Session


class Hypervisor(Session):
    def __init__(self, base_url):
        self.base_url = base_url
        super().__init__()

    def request(self, method, url, data=None, headers={}, **kwargs):
        if not url.startswith("http"):
            url = f"{self.base_url}/{url.lstrip('/')}"
        response = super().request(method, url, headers=headers, data=data, **kwargs)
        logging.debug(response.text)
        return response


def read_config(ctx, param, value):
    if value:
        with open(value) as config_file:
            ctx.default_map = json.load(config_file)
            return
    for file in [".qemuctl.json", "~/.qemuctl.json", "/etc/qemuctl.json"]:
        file = os.path.expanduser(file)
        if not os.path.exists(file):
            continue
        with open(file) as config_file:
            ctx.default_map = json.load(config_file)
            return


def sizeof_fmt(num, suffix='B'):
    magnitude = int(math.floor(math.log(num, 1024)))
    val = num / math.pow(1024, magnitude)
    if magnitude > 7:
        return '{:.1f}{}{}'.format(val, 'Yi', suffix)
    return '{:3.1f}{}{}'.format(val, ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi'][magnitude], suffix)


pass_hypervisor = click.make_pass_decorator(Hypervisor)


@click.group(context_settings=dict(auto_envvar_prefix="QEMU", show_default=True))
@click.option("--config", help="Location to a config file", is_eager=True, callback=read_config)
@click.option("--hypervisor", help="Hypervisor endpoint")
@click.option("--vnc-command", help="The vnc program to execute")
@click.option("-v", "--verbose", count=True, help="Verbose logging, repeat to increase verbosity")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, verbose, config, vnc_command, hypervisor):
    """
    Manage virtual machines using qemu.
    """
    logging.basicConfig(level=max(30 - verbose * 10, 10), format="[%(asctime)-15s] [%(levelname)s] %(message)s")
    ctx.obj = Hypervisor(base_url=hypervisor)


@cli.group()
def vms():
    """
    Manage virtual machines.
    """
    pass


@vms.command("list")
@click.option("--details", is_flag=True, help="Show more details")
@pass_hypervisor
def vms_list(hypervisor, details):
    """
    List virtual machines.
    """
    for vm in hypervisor.get("/vms").json():
        print("\t".join([
            vm["name"].ljust(30),
            vm["status"].rjust(8),
            vm["spec"]["memory"]["size"].rjust(8),
        ]))


@vms.command("show")
@click.argument("name")
@pass_hypervisor
def vms_show(hypervisor, name):
    """
    Show information about a virtual machine.
    """
    vm = hypervisor.get(f"/vms/{name}").json()
    print(f"Status: {vm['status']}")
    if vm["vnc"]:
        print(f"Display: {vm['vnc']}")
    print(f"Memory: {vm['spec']['memory']}")
    print(f"Cpu: {vm['spec']['smp']}")
    if vm["spec"]["drives"]:
        print("Drives:")
        for drive in vm["spec"]["drives"]:
            print(f"  - {drive}")
    if vm["spec"]["nics"]:
        print("Nics:")
        for nic in vm["spec"]["nics"]:
            print(f"  - {nic}")
    print(f"State: {vm['state']}")


@vms.command("display")
@click.argument("name")
@pass_hypervisor
@click.pass_context
def vms_display(ctx, hypervisor, name):
    """
    Open the console with vnc
    """
    vm = hypervisor.get(f"/vms/{name}").json()
    if not vm["vnc"]:
        print(f"Vm {name} is not running")
        return
    if ctx.find_root().params["vnc_command"]:
        subprocess.run(ctx.find_root().params["vnc_command"].format(vm["vnc"]), shell=True)
    else:
        print(vm["vnc"])


@vms.command("create")
@click.option("--dry-run", is_flag=True, help="Do not create the virtual machine")
@click.option("--snapshot", is_flag=True, help="write to temporary files instead of disk image files")
@click.option("--uefi", is_flag=True, help="boot vm in uefi mode")
@click.option("--memory", default="size=1G", help="configure RAM")
@click.option("--smp", default="cores=2", help="configure CPU topology")
@click.option("--rtc", default="base=utc,driftfix=slew", help="configure the clock")
@click.option("--smbios", default=None, help="specify SMBIOS fields")
@click.option("--boot", default=None, help="configure boot order")
@click.option("--cdrom", default=None, help="use file as IDE cdrom image")
@click.option("--device", "devices", multiple=True, default=[], help="configure one or more devices")
@click.option("--drive", "drives", multiple=True, default=[], help="configure one or more HDDs")
@click.option("--nic", "nics", multiple=True, default=["type=none"], help="configure one or more NICs")
@click.argument("name")
@pass_hypervisor
@click.pass_context
def vms_create(ctx, hypervisor, dry_run, **spec):
    """
    Create a virtual machine.

    Change cores or memory:
    \b
        --smp cores=2
        --memory 2G

    \b
    Add drives:
    \b
        --drive disk01.qcow2
        --drive size=50G
        --drive file=disk01.qcow2
        --drive file=disk01.qcow2,size=50G
        --drive file=/fuu/bar/test.raw
        --drive file=disk01.qcow2,backing_file=/fuu/bar/test.qcow2
        --drive backing_file=/fuu/bar/test.qcow2

    \b
    Add networks:
    \b
        --nic br0
        --nic type=bridge,br=br0
        --nic br0,model=virtio-net-pci
        --nic br0,mac=aa:bb:cc:dd:ee:ff

    \b
    Set boot order:
    \b
        --boot order=n
        --boot order=d

    \b
    Set serial number:
    \b
        --smbios type=1,serial=89n1jk2k

    \b
    Add a cdrom:
    \b
        --cdrom /var/lib/qemu/images/Fedora-Server-netinst-x86_64-33-1.2.iso
    """
    vm = hypervisor.post("/vms", json=spec).json()
    print(f"Vm {vm['name']} created: {vm['vnc']}")
    if ctx.find_root().params["vnc_command"]:
        subprocess.run(ctx.find_root().params["vnc_command"].format(vm["vnc"]), shell=True)


@vms.command("start")
@click.argument("name")
@pass_hypervisor
@click.pass_context
def vms_start(ctx, hypervisor, name):
    """
    Start a virtual machine.
    """
    vm = hypervisor.post(f"/vms/{name}/start").json()
    print(f"Vm {name} started: {vm['vnc']}")
    if ctx.find_root().params["vnc_command"]:
        subprocess.run(ctx.find_root().params["vnc_command"].format(vm["vnc"]), shell=True)


@vms.command("restart")
@click.argument("name")
@pass_hypervisor
def vms_restart(hypervisor, name):
    """
    Restart a virtual machine.
    """
    vm = hypervisor.post(f"/vms/{name}/restart").json()
    print(f"Vm {name} restarted: {vm['vnc']}")


@vms.command("stop")
@click.option("--force", is_flag=True, help="Stop the vm using force.")
@click.argument("name")
@pass_hypervisor
def vms_stop(hypervisor, name, force):
    """
    Stop a virtual machine.
    """
    hypervisor.post(f"/vms/{name}/stop")
    print(f"Vm {name} stopped")


@vms.command("monitor")
@click.argument("name")
@click.argument("command")
@click.argument("arguments", nargs=-1)
@pass_hypervisor
def vms_monitor(hypervisor, name, command, arguments):
    """
    Send qmp commands to a virtual machine.

    \b
    To powerdown a VM
    \b
        qemuctl vms monitor <name> system_powerdown

    \b
    To see all available commands
    \b
        qemuctl vms monitor <name> query-commands

    \b
    Eject a cd-rom
    \b
        qemuctl vms monitor <name> query-block
        qemuctl vms monitor <name> eject id=sr01

    \b
    List internal object tree
    \b
        qemuctl vms monitor <name> qom-list 'path=/machine/peripheral-anon/device[0]'
        qemuctl vms monitor <name> qom-get 'path=/machine/peripheral-anon/device[0]' property=mac
    """
    data = {
        'command': command,
        'arguments': {key: value for key, value in [arg.split("=") for arg in arguments]},
    }
    result = hypervisor.post(f"/vms/{name}/monitor", json=data).json()
    print(json.dumps(result, indent=2))


@vms.command("destroy")
@click.argument("name")
@pass_hypervisor
def vms_destroy(hypervisor, name):
    """
    Destroy a virtual machine.
    """
    hypervisor.delete(f"/vms/{name}")
    print(f"Vm {name} destroyed")


@cli.group()
def images():
    """
    Manage images.
    """
    pass


@images.command("list")
@click.option("--details", is_flag=True, help="Show more details")
@pass_hypervisor
def images_list(hypervisor, details):
    """
    List all available images.
    """
    for image in hypervisor.get("/images").json():
        print("\t".join([
            image["name"].ljust(40),
            sizeof_fmt(image["spec"]["actual-size"]).rjust(8),
            sizeof_fmt(image["spec"]["virtual-size"]).rjust(8),
        ]))


@images.command("show")
@click.argument("name")
@pass_hypervisor
def images_show(hypervisor, name):
    """
    Show information about an image.
    """
    image = hypervisor.get(f"/images/{name}").json()
    print(json.dumps(image, indent=2))


@images.command("delete")
@click.argument("name")
@pass_hypervisor
def images_delete(hypervisor, name):
    """
    Delete an image.
    """
    hypervisor.delete(f"/images/{name}")
    print(f"Image {name} deleted")


@cli.group()
def networks():
    """
    Manage networks.
    """
    pass


@networks.command("list")
@click.option("--details", is_flag=True, help="Show more details")
@pass_hypervisor
def networks_list(hypervisor, details):
    """
    List all available networks.
    """
    for network in hypervisor.get("/networks").json():
        print(network["name"])


@networks.command("show")
@click.argument("name")
@pass_hypervisor
def networks_show(hypervisor, name):
    """
    Show detailed information for a network.
    """
    network = hypervisor.get(f"/networks/{name}").json()
    print(f"Name: {name}")
    print("Ip: " + ", ".join([addr['local'] for addr in network['address'][0]['addr_info']]))
    print("Leases:")
    for lease in network['leases']:
        print(f"  {lease['mac']} => {lease['ip']}")
    print("Stats:")
    print(f"  Received: {sizeof_fmt(network['stats']['kernel'][name]['rx_bytes'])}")
    print(f"  Sent: {sizeof_fmt(network['stats']['kernel'][name]['tx_bytes'])}")


@networks.command("create")
@click.option("--ip-range", help="Assign an ip address to this network")
@click.option("--dhcp/--no-dhcp", default=True, help="Enable dhcp server on this network")
@click.argument("name")
@pass_hypervisor
def networks_create(hypervisor, **spec):
    """
    Create a network.
    """
    hypervisor.post("/networks", json=spec)
    print(f"Network {spec['name']} created")


@networks.command("destroy")
@click.argument("name")
@pass_hypervisor
def networks_destroy(hypervisor, name):
    """
    Destroy a network.
    """
    hypervisor.delete(f"/networks/{name}")
    print(f"Network {name} destroyed")

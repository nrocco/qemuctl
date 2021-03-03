import click
import ipaddress
import json
import logging
import os
import subprocess

from qemu import __version__
from requests import Session


class Hypervisor(Session):
    def __init__(self, base_url):
        self.base_url = base_url
        super().__init__()

    def request(self, method, url, data=None, headers={}, **kwargs):
        if not url.startswith('http'):
            url = '{}/{}'.format(self.base_url, url.lstrip('/'))
        return super().request(method, url, headers=headers, data=data, **kwargs)


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
            ctx.default_map = json.load(config_file)
            return


pass_hypervisor = click.make_pass_decorator(Hypervisor)


@click.group(context_settings=dict(auto_envvar_prefix="QEMU", show_default=True))
@click.option("--config", default=[".qemuctl.json", "~/.qemuctl.json", "/etc/qemuctl.json"], help="Location to a config file", is_eager=True, callback=read_config)
@click.option("--hypervisor", help="Hypervisor endpoint")
@click.option("-v", "--verbose", count=True, help="Verbose logging, repeat to increase verbosity")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, verbose, config, hypervisor):
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
        print(vm['name'])


@vms.command("show")
@click.argument("name")
@pass_hypervisor
def vms_show(hypervisor, name):
    """
    Show information about a virtual machine.
    """
    vm = hypervisor.get(f"/vms/{name}").json()
    print(f"{vm['name']}:")
    print(f"  Status: {vm['status']['status']}")
    if vm['vnc']:
        print(f"  Display: {vm['vnc']['url']}")
    # if vm['nics']:
    #     print(f"  Mac: {vm['nics'][0]['mac']}")
    #     lease = [lease for lease in hypervisor.get_leases(vm['nics'][0]['br']) if lease["mac"] == vm['nics'][0]['mac']]  # TODO this assumes dhcp is enabled on bridge
    #     if lease:
    #         print(f"  Ip: {lease[0]['ip']}")
    #         print(f"  Hostname: {lease[0]['host']}")


@vms.command("display")
@click.argument("name")
@pass_hypervisor
def vms_display(hypervisor, name):
    """
    Open the console with vnc
    """
    vm = hypervisor.get(f"/vms/{name}").json()
    subprocess.run(["open", vm['vnc']['url']])


@vms.command("create")
@click.option("--dry-run", is_flag=True, help="Do not create the virtual machine")
@click.option("--snapshot", is_flag=True, help="write to temporary files instead of disk image files")
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
def vms_create(hypervisor, dry_run, **spec):
    """
    Create a virtual machine.

    Change cores or memory:
    \b
        --smp cores=2
        --memory 2G

    \b
    Add drives:
    \b
        --drive disk01.qcow2                                            # if exists ignore else create and assume size X
        --drive file=disk01.qcow2                                       # if exists ignore else create and assume size X
        --drive file=disk01.qcow2,size=50G                              # if exists ignore else create with size 50G
        --drive file=/fuu/bar/test.raw                                  # fail if not exists
        --drive file=disk01.qcow2,backing_file=/fuu/bar/test.qcow2      # if exists ignore else create file with backing file
        --drive backing_file=/fuu/bar/test.qcow2                        # implicitly create new disk with backing file

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
    print(f"Vm {vm['name']} created: {vm['vnc']['url']}")


@vms.command("start")
@click.argument("name")
@pass_hypervisor
def vms_start(hypervisor, name):
    """
    Start a virtual machine.
    """
    vm = hypervisor.post(f"/vms/{name}/start").json()
    print(f"Vm {name} started: {vm['vnc']['url']}")


@vms.command("restart")
@click.argument("name")
@pass_hypervisor
def vms_restart(hypervisor, name):
    """
    Restart a virtual machine.
    """
    vm = hypervisor.post(f"/vms/{name}/restart").json()
    print(f"Vm {name} restarted: {vm['vnc']['url']}")


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
    system_powerdown
    qom-list 'path=/machine/peripheral-anon/device[0]'
    qom-get 'path=/machine/peripheral-anon/device[0]' property=mac
    """
    arguments = {key: value for key, value in [arg.split("=") for arg in arguments]}
    with hypervisor.get_qmp(name) as qmp:
        result = qmp.execute(command, **arguments)
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
    for name in hypervisor.list_images(details):
        print(name)


@images.command("show")
@click.argument("name")
@pass_hypervisor
def images_show(hypervisor, name):
    """
    Show information about an image.
    """
    print(json.dumps(hypervisor.get_image(name), indent=2))


@images.command("delete")
@click.argument("name")
@pass_hypervisor
def images_delete(hypervisor, name):
    """
    Delete an image.
    """
    hypervisor.delete_image(name)
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
    for name in hypervisor.list_networks(details):
        print(name)


@networks.command("show")
@click.argument("name")
@pass_hypervisor
def networks_show(hypervisor, name):
    print(json.dumps(json.loads(hypervisor.run(["ip", "-j", "route", "show", "dev", name]).stdout), indent=2))
    print(json.dumps(json.loads(hypervisor.run(["ip", "-j", "neigh", "show", "dev", name]).stdout), indent=2))
    print(json.dumps(json.loads(hypervisor.run(["ip", "-j", "addr", "show", "dev", name]).stdout), indent=2))
    print(json.dumps(json.loads(hypervisor.run(["ip", "-j", "link", "show", "master", name, "type", "bridge_slave"]).stdout), indent=2))
    print(json.dumps(json.loads(hypervisor.run(["ifstat", "-j", name]).stdout), indent=2))


@networks.command("create")
@click.option("--ip-range", help="Assign an ip address to this network")
@click.option("--dhcp/--no-dhcp", default=True, help="Enable dhcp server on this network")
@click.argument("name")
@pass_hypervisor
def networks_create(hypervisor, name, dhcp, ip_range):
    """
    Create a network.
    """
    if ip_range:
        ip_range = ipaddress.ip_network(ip_range)
    hypervisor.create_network(name, dhcp, ip_range)
    print(f"Network {name} created")


@networks.command("destroy")
@click.argument("name")
@pass_hypervisor
def networks_destroy(hypervisor, name):
    """
    Destroy a network.
    """
    hypervisor.destroy_network(name)
    print(f"Network {name} destroy")


@networks.command("leases")
@click.argument("name")
@pass_hypervisor
def networks_leases(hypervisor, name):
    """
    List leases for a network.
    """
    print(json.dumps(hypervisor.get_leases(name), indent=2))


@cli.group()
def system():
    """
    Manage the hypervisor itself.
    """
    pass


@system.command("show")
@pass_hypervisor
def system_show(hypervisor):
    """
    View all objects on this hypervisor.
    """
    print(hypervisor.run(["tree", hypervisor.state_directory]).stdout)

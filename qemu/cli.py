import click
import json
import logging
import math
import os
import subprocess

from . import __version__
from .hypervisor_ssh import HypervisorSSH
from .specs import NetworkSpec
from .specs import VmSpec


def read_config(ctx, param, value):
    if value:
        with open(value) as config_file:
            ctx.default_map = json.load(config_file)
            return
    for file in [".qemuctl.json", "~/.config/qemuctl/config.json", "/etc/qemuctl.json"]:
        file = os.path.expanduser(file)
        if not os.path.exists(file):
            continue
        with open(file) as config_file:
            ctx.default_map = json.load(config_file)
            return


def sizeof_fmt(num, suffix='B'):
    if num == 0:
        return '0{}'.format(suffix)
    magnitude = int(math.floor(math.log(num, 1024)))
    val = num / math.pow(1024, magnitude)
    if magnitude > 7:
        return '{:.1f}{}{}'.format(val, 'Yi', suffix)
    return '{:3.1f}{}{}'.format(val, ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi'][magnitude], suffix)


pass_hypervisor = click.make_pass_decorator(HypervisorSSH)


@click.group(context_settings=dict(auto_envvar_prefix="QEMU", show_default=True))
@click.option("--config", help="Location to a config file", is_eager=True, callback=read_config)
@click.option("--hypervisor", help="Hypervisor endpoint")
@click.option("--vnc-command", help="The vnc program to execute")
@click.option("--vnc-address", help="The vnc program to execute")
@click.option("--vnc-password", help="The vnc program to execute")
@click.option("-v", "--verbose", count=True, help="Verbose logging, repeat to increase verbosity")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, verbose, config, vnc_command, vnc_address, vnc_password, hypervisor):
    """
    Manage virtual machines using qemu.
    """
    logging.basicConfig(level=max(30 - verbose * 10, 10), format="[%(asctime)-15s] [%(levelname)s] %(message)s")
    ctx.obj = HypervisorSSH(hypervisor, vnc_address=vnc_address, vnc_password=vnc_password)


@cli.command("check")
@pass_hypervisor
def check(hypervisor):
    """
    Check if the hypervisor meets the requirements.
    """
    print("Check binaries:")
    print(" - {}".format(hypervisor.exec(["type", "find"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "install"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "ifstat"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "socat"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "dnsmasq"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "ip"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "qemu-system-x86_64"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "qemu-img"]).strip()))
    print(" - {}".format(hypervisor.exec(["type", "iptables"]).strip()))
    print("Check ip forwarding:")
    print(" - {}".format(hypervisor.exec(["sysctl", "net.ipv4.ip_forward"]).strip()))


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
    for vm in hypervisor.vms.all():
        print("\t".join([
            vm.name.ljust(30),
            ("running" if vm.is_running else "stopped").rjust(8),
            vm.spec["memory"]["size"].rjust(8),
        ]))


@vms.command("show")
@click.argument("name")
@pass_hypervisor
def vms_show(hypervisor, name):
    """
    Show information about a virtual machine.
    """
    vm = hypervisor.vms.get(name)
    spec = vm.spec
    print(f"Name: {name}")
    print(f"Memory: {spec['memory']['size']}")
    print(f"Cpu: {spec['smp']['cores']}")
    if vm.is_running:
        print("Status: running")
        with vm.monitor as monitor:
            vnc_data = monitor.execute("query-vnc")
        print(f"Display: vnc://:{spec['vnc']['password']}@{vnc_data['host']}:{vnc_data['service']}")
    else:
        print("Status: stopped")
    print(f"Ip: {vm.address}")
    if spec["drives"]:
        print("Drives:")
        for drive in spec["drives"]:
            print(f"  - {drive}")
    if spec["nics"]:
        print("Nics:")
        for nic in spec["nics"]:
            print(f"  - {nic}")


@vms.command("console")
@click.argument("name")
@pass_hypervisor
@click.pass_context
def vms_console(ctx, hypervisor, name):
    """
    Open the console with vnc
    """
    vm = hypervisor.vms.get(name)
    if not vm.is_running:
        print(f"Vm {name} is not running")
        ctx.exit(1)
    with vm.monitor as monitor:
        vnc_data = monitor.execute("query-vnc")
    vnc_uri = f"vnc://:{vm.spec['vnc']['password']}@{vnc_data['host']}:{vnc_data['service']}"
    if ctx.find_root().params["vnc_command"]:
        subprocess.run(ctx.find_root().params["vnc_command"].format(vnc_uri), shell=True)
    else:
        print(vnc_uri)


@vms.command("ssh")
@click.argument("name")
@pass_hypervisor
@click.pass_context
def vms_ssh(ctx, hypervisor, name):
    """
    Setup an ssh session to the vm
    """
    vm = hypervisor.vms.get(name)
    if not vm.is_running:
        print(f"Vm {name} is not running")
        ctx.exit(1)
    ip = vm.address
    if not ip:
        print(f"Vm {name} does not have an ip")
        ctx.exit(1)
    subprocess.run(f"ssh {ip}", shell=True)


@vms.command("create")
@click.option("--console/--no-console", is_flag=True, default=True, help="Open the VNC console after creating the machine")
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
def vms_create(ctx, hypervisor, console, dry_run, **spec):
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
        --drive file=disk01.qcow2,backing_file=disks/test.qcow2
        --drive backing_file=disks/bar/test.qcow2

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
        --boot order=c,once=d

    \b
    Set serial number:
    \b
        --smbios type=1,serial=89n1jk2k

    \b
    Add a cdrom:
    \b
        --cdrom isos/Fedora-Server-netinst-x86_64-33-1.2.iso
    """
    spec = VmSpec(spec)
    if dry_run:
        print(json.dumps(spec, indent=2))
        ctx.exit(0)
    vm = hypervisor.vms.create(spec)
    vm.start()
    print(f"Vm {vm.name} created")
    with vm.monitor as monitor:
        vnc_data = monitor.execute("query-vnc")
    vnc_uri = f"vnc://:{vm.spec['vnc']['password']}@{vnc_data['host']}:{vnc_data['service']}"
    if ctx.find_root().params["vnc_command"]:
        subprocess.run(ctx.find_root().params["vnc_command"].format(vnc_uri), shell=True)
    else:
        print(vnc_uri)


@vms.command("start")
@click.argument("name")
@pass_hypervisor
@click.pass_context
def vms_start(ctx, hypervisor, name):
    """
    Start a virtual machine.
    """
    vm = hypervisor.vms.get(name)
    vm.start()
    print(f"Vm {name} started")
    # TODO optionally open the vnc console


@vms.command("restart")
@click.argument("name")
@pass_hypervisor
def vms_restart(hypervisor, name):
    """
    Restart a virtual machine.
    """
    vm = hypervisor.vms.get(name)
    vm.restart()
    print(f"Vm {name} restarted")
    # TODO optionally open the vnc console


@vms.command("stop")
@click.option("--force", is_flag=True, help="Stop the vm using force.")
@click.argument("name")
@pass_hypervisor
def vms_stop(hypervisor, name, force):
    """
    Stop a virtual machine.
    """
    vm = hypervisor.vms.get(name)
    vm.stop()
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
    arguments = {key: value for key, value in [arg.split("=") for arg in arguments]}
    vm = hypervisor.vms.get(name)
    with vm.monitor as monitor:
        result = monitor.execute(command, **arguments)
    print(json.dumps(result, indent=2))


@vms.command("destroy")
@click.argument("name")
@pass_hypervisor
def vms_destroy(hypervisor, name):
    """
    Destroy a virtual machine.
    """
    vm = hypervisor.vms.get(name)
    vm.destroy()
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
    for image in hypervisor.images.all():
        print("\t".join([
            image.name.ljust(40),
            sizeof_fmt(image.spec["actual-size"]).rjust(8),
            sizeof_fmt(image.spec["virtual-size"]).rjust(8),
        ]))


@images.command("show")
@click.argument("name")
@pass_hypervisor
def images_show(hypervisor, name):
    """
    Show information about an image.
    """
    image = hypervisor.images.get(name)
    print(json.dumps(image.spec, indent=2))


@images.command("delete")
@click.argument("name")
@pass_hypervisor
def images_delete(hypervisor, name):
    """
    Delete an image.
    """
    image = hypervisor.images.get(name)
    image.delete()
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
    for network in hypervisor.networks.all():
        print(network.name)


@networks.command("show")
@click.argument("name")
@pass_hypervisor
def networks_show(hypervisor, name):
    """
    Show detailed information for a network.
    """
    network = hypervisor.networks.get(name)
    print(f"Name: {network.name}")
    print("Ip: " + ", ".join([addr['local'] for addr in network.address[0]['addr_info']]))
    print("Leases:")
    for lease in network.leases:
        print(f"  {lease['mac']} => {lease['ip']}")
    print("Stats:")
    print(f"  Received: {sizeof_fmt(network.stats['kernel'][name]['rx_bytes'])}")
    print(f"  Sent: {sizeof_fmt(network.stats['kernel'][name]['tx_bytes'])}")


@networks.command("create")
@click.option("--ip-range", help="Assign an ip address to this network")
@click.option("--dhcp/--no-dhcp", default=True, help="Enable dhcp server on this network")
@click.argument("name")
@pass_hypervisor
def networks_create(hypervisor, **spec):
    """
    Create a network.
    """
    spec = NetworkSpec(spec)
    network = hypervisor.networks.create(spec)
    network.start()
    print(f"Network {network.name} created")


@networks.command("destroy")
@click.argument("name")
@pass_hypervisor
def networks_destroy(hypervisor, name):
    """
    Destroy a network.
    """
    network = hypervisor.networks.get(name)
    network.destroy()
    print(f"Network {name} destroyed")

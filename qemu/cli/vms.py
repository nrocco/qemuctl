import click
import json

from .utils import pass_hypervisor
from qemu.specs import Vm


@click.group()
def vms():
    """
    Manage virtual machines
    """
    pass


@vms.command("list")
@pass_hypervisor
def list_(hypervisor):
    """
    List virtual machines
    """
    for name in hypervisor.list_vms():
        print(name)


@vms.command("info")
@click.argument("name")
@pass_hypervisor
def info(hypervisor, name):
    """
    Get information about a virtual machine
    """
    with hypervisor.get_qmp(name) as qmp:
        status = qmp.execute("query-status")
        vnc = qmp.execute("query-vnc")
    print(f"{name}:")
    print(f"  Status: {status['status']}")
    print(f"  Display: vnc://:{hypervisor.vnc_password}@{vnc['host']}:{vnc['service']}")
    # TODO get mac address
    # TODO get ip address


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
def create(hypervisor, dry_run, **spec):
    """
    Create a virtual machine

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
        --nic br0,driver=virtio-net
        --nic br0,driver=virtio-net,mac=aa:bb:cc:dd:ee:ff

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
    vm = Vm(spec, hypervisor.default_opts_for_vm(spec["name"]))
    if dry_run:
        print(json.dumps(vm, indent=2))
        print(f"qemu-system-{vm['arch']} " + " ".join(vm.to_args()))
    else:
        hypervisor.create_vm(vm)
    print(f"Vm {vm['name']} created")


@vms.command("start")
@click.argument("name")
@pass_hypervisor
def start(hypervisor, name):
    """
    Start a virtual machine
    """
    with hypervisor.get_qmp(name) as qmp:
        qmp.execute("cont")
    print(f"Vm {name} started")


@vms.command("restart")
@click.argument("name")
@pass_hypervisor
def restart(hypervisor, name):
    """
    Restart a virtual machine
    """
    with hypervisor.get_qmp(name) as qmp:
        qmp.execute("system_reset")
    print(f"Vm {name} restarted")


@vms.command("stop")
@click.argument("name")
@pass_hypervisor
def stop(hypervisor, name):
    """
    Stop a virtual machine
    """
    with hypervisor.get_qmp(name) as qmp:
        qmp.execute("stop")
    print(f"Vm {name} stopped")


@vms.command("monitor")
@click.argument("name")
@click.argument("command")
@click.argument("arguments", nargs=-1)
@pass_hypervisor
def monitor(hypervisor, name, command, arguments):
    """
    Send qmp commands to a virtual machine

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
def destroy(hypervisor, name):
    """
    Destroy a virtual machine
    """
    hypervisor.remove_vm(name)
    print(f"Vm {name} destroyed")

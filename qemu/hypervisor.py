import json
import os

from .qmp import Qmp
from .ssh import Ssh
from qemu.utils import dict_to_qemu_arg


class Hypervisor:
    def __init__(self, host, state_directory, vnc_address, vnc_password):
        self.host = host
        self.state_directory = state_directory
        self.vnc_address = vnc_address
        self.vnc_password = vnc_password

    def run(self, command):
        return Ssh(self.host, command)

    def get_qmp(self, name):
        return Qmp(self.host, os.path.join(self.state_directory, 'vms', name, "qmp.sock"))

    def list_vms(self):
        result = self.run(["ls", os.path.join(self.state_directory, 'vms')])
        return result.stdout.splitlines()

    def create_vm(self, spec):
        # TODO check if vm is not already created,
        vm_chroot = os.path.join(self.state_directory, 'vms', spec['name'])
        args = [
            f"qemu-system-{spec['arch']}",
            "-enable-kvm",
            "-daemonize",
            "-S",
            "-nodefaults",
            "-chroot", vm_chroot,
            "-name", spec['name'],
            "-qmp", "unix:{},server,nowait".format(os.path.join(vm_chroot, 'qmp.sock')),
            "-pidfile", os.path.join(vm_chroot, 'pidfile'),
            "-m", dict_to_qemu_arg(spec['memory']),
            "-uuid", spec['uuid'],
            "-vga", spec['vga'],
            "-cpu", spec['cpu'],
            "-smp", dict_to_qemu_arg(spec['smp']),
            "-rtc", dict_to_qemu_arg(spec['rtc']),
        ]
        if 'spec' in spec and not spec['hpet']:
            args += ["-no-hpet"]
        if 'shutdown' in spec and not spec['shutdown']:
            args += ["-no-shutdown"]
        if self.vnc_address:
            args += "-display", f"vnc={self.vnc_address}:0,to=100,password"
        if 'smbios' in spec and spec['smbios']:
            args += "-smbios", dict_to_qemu_arg(spec['smbios'])
        if 'boot' in spec and spec['boot']:
            args += "-boot", dict_to_qemu_arg(spec['boot'])
        if 'cdrom' in spec and spec['cdrom']:
            args += "-cdrom", dict_to_qemu_arg(spec['cdrom'])
        if 'snapshot' in spec and spec['snapshot']:
            args += ["-snapshot"]
        for drive in spec['drives']:
            if 'file' in drive and not drive['file'].startswith('/'):
                drive['file'] = os.path.join(vm_chroot, drive['file'])
            args += "-drive", dict_to_qemu_arg(drive)
        for network in spec['networks']:
            args += "-netdev", f"type={network['type']},id={network['id']},br={network['bridge']}"
            args += "-device", f"driver={network['driver']},netdev={network['id']},mac={network['mac']}"
        for device in spec['devices']:
            args += "-device", dict_to_qemu_arg(device)
        # print(" ".join(args))
        # return
        self.run(["mkdir", "-p", vm_chroot])
        self.run(args)
        with self.get_qmp(spec['name']) as qmp:
            qmp.execute("change-vnc-password", password=self.vnc_password)
            qmp.execute("cont")

    def remove_vm(self, vm):
        # TODO check if vm is running
        with self.get_qmp(vm) as qmp:
            qmp.execute("quit")
        self.run(["rm", "-rf", os.path.join(self.state_directory, 'vms', vm)])

    def list_images(self):
        result = self.run(["ls", "-lh", os.path.join(self.state_directory, 'images')])
        return result.stdout.splitlines()

    def get_image(self, image):
        result = self.run(["qemu-img", "info", "--backing-chain", "--output=json", os.path.join(self.state_directory, 'images', image)])
        return json.loads(result.stdout)

    def remove_image(self, image):
        self.run(["rm", os.path.join(self.state_directory, 'images', image)])

    def get_leases(self, network):
        leases = []
        result = self.run(["cat", os.path.join(self.state_directory, "networks", network, f"{network}.leases")])
        for line in result.stdout.splitlines():
            data = line.split(" ")
            leases.append({
                'timestamp': data[0],
                'mac': data[1],
                'ip': data[2],
                'host': data[3],
                'id': data[4],
            })
        return leases

    def start_network(self, network):
        self.run(["dnsmasq", "--conf-file={}".format(os.path.join(self.state_directory, "networks", network, f"{network}.conf"))])

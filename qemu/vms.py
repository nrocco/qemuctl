import json
import os
import shutil

from .qmp import Qmp
from .specs import VmSpec


class Vm:
    @staticmethod
    def create_from_spec(hypervisor, spec):
        vm = Vm(hypervisor, spec["name"])
        os.makedirs(vm.directory)
        spec.update({
            "chroot": vm.directory,
            "pidfile": "pidfile",
            "runas": "qemu",
            "qmp": "unix:qmp.sock,server=yes,wait=no",
            "vnc": {
                "vnc": hypervisor.config["vnc"]["address"],
                "to": "100",
                "password": hypervisor.config["vnc"]["password"],
            },
        })
        with open(os.path.join(vm.directory, "spec.json"), "w") as file:
            json.dump(spec, file)
        for drive in spec["drives"]:
            if "OVMF_CODE.fd" in drive["file"]:
                vm.hypervisor.exec(["install", "--no-target-directory", "--owner=qemu", "--group=kvm", "--mode=775", vm.hypervisor.config['uefi']['code'], drive["file"]], cwd=vm.directory)
                continue
            if "OVMF_VARS.fd" in drive["file"]:
                vm.hypervisor.exec(["install", "--no-target-directory", "--owner=qemu", "--group=kvm", "--mode=775", vm.hypervisor.config['uefi']['vars'], drive["file"]], cwd=vm.directory)
                continue
            if "backing_file" in drive:
                src = hypervisor.images.get(drive["backing_file"]).file
                dst = os.path.join(vm.directory, drive["backing_file"])
                os.makedirs(os.path.dirname(dst))
                os.link(src, dst)
            vm.hypervisor.exec(drive.to_qemu_img_args(), cwd=vm.directory)
        if "cdrom" in spec and spec["cdrom"]:
            src = hypervisor.images.get(spec["cdrom"]).file
            dst = os.path.join(vm.directory, spec["cdrom"])
            os.makedirs(os.path.dirname(dst)) # TODO this assumes isos are stored in images/subfolder!
            os.link(src, dst)
        return vm

    def __init__(self, hypervisor, name):
        self.hypervisor = hypervisor
        self.name = name
        self.directory = os.path.join(self.hypervisor.vms.directory, self.name)

    def __repr__(self):
        return f"<Vm {self.name}>"

    @property
    def spec(self):
        with open(os.path.join(self.directory, "spec.json"), "r") as file:
            data = json.load(file)
        return VmSpec(data)

    @property
    def drives(self):
        drives = []
        for drive in self.spec["drives"]:
            result = self.hypervisor.exec(["qemu-img", "info", "--force-share", "--output=json", drive["file"]], cwd=self.directory)
            drives.append(json.loads(result.stdout))
        return drives

    @property
    def monitor(self):
        return Qmp(os.path.join(self.directory, "qmp.sock"))

    @property
    def is_running(self):
        pidfile = os.path.join(self.directory, "pidfile")
        if not os.path.isfile(pidfile):
            return False
        return self.hypervisor.pid_exists(pidfile, "qemu")

    def start(self):
        spec = self.spec
        self.hypervisor.exec(spec.to_qemu_args(), cwd=self.directory)
        with self.monitor as monitor:
            if spec["vnc"]["password"]:
                monitor.execute("change-vnc-password", password=spec["vnc"]["password"])
            monitor.execute("cont")
        return self

    def restart(self):
        with self.monitor as monitor:
            monitor.execute("system_reset")
        return self

    def stop(self):
        with self.monitor as monitor:
            monitor.execute("quit")
        return self

    def destroy(self):
        self.hypervisor.pid_kill(os.path.join(self.directory, "pidfile"), "qemu")
        shutil.rmtree(self.directory)


class Vms:
    def __init__(self, hypervisor):
        self.hypervisor = hypervisor
        self.directory = os.path.join(hypervisor.directory, "vms")

    def __contains__(self, value):
        return os.path.isdir(os.path.join(self.directory, value))

    def all(self):
        if not os.path.isdir(self.directory):
            return []
        return [Vm(self.hypervisor, name) for name in os.listdir(self.directory)]

    def get(self, name):
        if name not in self:
            raise Exception(f"Vm {name} does not exist")
        return Vm(self.hypervisor, name)

    def create(self, spec):
        if spec["name"] in self:
            raise Exception("Vm already exists")
        return Vm.create_from_spec(self.hypervisor, spec)

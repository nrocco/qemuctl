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
            "pidfile": f"{vm.directory}/pidfile",
            "runas": "qemu",
            "qmp": f"unix:{vm.directory}/qmp.sock,server=yes,wait=no",
            "vnc": {
                "vnc": os.environ["QEMUCTL_VNC_ADDRESS"],
                "to": "100",
                "password": os.environ["QEMUCTL_VNC_PASSWORD"],
            },
        })
        with open(os.path.join(vm.directory, "spec.json"), "w") as file:
            json.dump(spec, file)
        for drive in spec["drives"]:
            if "OVMF_CODE.fd" in drive["file"]:
                vm.hypervisor.exec(["install", "--no-target-directory", "--owner=qemu", "--group=kvm", "--mode=775", "/usr/share/OVMF/OVMF_CODE.fd", drive["file"]])
            if "OVMF_VARS.fd" in drive["file"]:
                vm.hypervisor.exec(["install", "--no-target-directory", "--owner=qemu", "--group=kvm", "--mode=775", "/usr/share/OVMF/OVMF_VARS.fd", drive["file"]])
            if os.path.isfile(drive["file"]):
                continue
            if "size" not in drive and "backing_file" not in drive:
                continue
            vm.hypervisor.exec(drive.to_qemu_img_args())
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
        return [json.loads(self.hypervisor.exec(["qemu-img", "info", "--force-share", "--output=json", drive["file"]]).stdout) for drive in self.spec["drives"]]

    @property
    def monitor(self):
        return Qmp(os.path.join(self.directory, "qmp.sock"))

    @property
    def is_running(self):
        return os.path.isfile(os.path.join(self.directory, "pidfile"))

    def start(self):
        spec = self.spec
        self.hypervisor.exec(spec.to_qemu_args())
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

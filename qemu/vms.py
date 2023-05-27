import json
import os

from .specs import VmSpec


class Vm:
    @staticmethod
    def create_from_spec(hypervisor, spec):
        vm = Vm(hypervisor, spec["name"])
        vm.hypervisor.make_dir(vm.directory)
        spec.update({
            "chroot": vm.directory,
            "pidfile": "pidfile",
            "runas": "nobody",
            "qmp": "unix:qmp.sock,server=yes,wait=no",
            "vnc": {
                "vnc": vm.hypervisor.config["vnc"]["address"],
                "to": "100",
                "password": vm.hypervisor.config["vnc"]["password"],
            },
        })
        with vm.hypervisor.open_file(os.path.join(vm.directory, "spec.json"), "w") as file:
            json.dump(spec, file)
        for drive in spec["drives"]:
            if "uefi_code.fd" in drive["file"]:
                vm.hypervisor.exec(["install", "--no-target-directory", "--owner=nobody", "--group=kvm", "--mode=775", vm.hypervisor.config['uefi'][spec['arch']]['code'], drive["file"]], cwd=vm.directory)
                continue
            if "uefi_vars.fd" in drive["file"]:
                vm.hypervisor.exec(["install", "--no-target-directory", "--owner=nobody", "--group=kvm", "--mode=775", vm.hypervisor.config['uefi'][spec['arch']]['vars'], drive["file"]], cwd=vm.directory)
                continue
            if "backing_file" in drive:
                src = vm.hypervisor.images.get(drive["backing_file"]).file
                dst = os.path.join(vm.directory, drive["backing_file"])
                vm.hypervisor.make_dir(os.path.dirname(dst))
                vm.hypervisor.symlink(src, dst)
            vm.hypervisor.exec(drive.to_qemu_img_args(), cwd=vm.directory)
        if "cdrom" in spec and spec["cdrom"]:
            src = vm.hypervisor.images.get(spec["cdrom"]).file
            dst = os.path.join(vm.directory, spec["cdrom"])
            vm.hypervisor.make_dir(os.path.dirname(dst))  # TODO this assumes isos are stored in images/subfolder!
            vm.hypervisor.symlink(src, dst)
        return vm

    def __init__(self, hypervisor, name):
        self.hypervisor = hypervisor
        self.name = name
        self.directory = os.path.join(self.hypervisor.vms.directory, self.name)

    def __repr__(self):
        return f"<Vm {self.name}>"

    @property
    def spec(self):
        with self.hypervisor.open_file(os.path.join(self.directory, "spec.json"), "r") as file:
            data = json.load(file)
        return VmSpec(data)

    @property
    def drives(self):
        drives = []
        for drive in self.spec["drives"]:
            result = self.hypervisor.exec(["qemu-img", "info", "--force-share", "--output=json", drive["file"]], cwd=self.directory)
            drives.append(json.loads(result))
        return drives

    @property
    def monitor(self):
        return self.hypervisor.qmp(os.path.join(self.directory, "qmp.sock"))

    @property
    def is_running(self):
        pidfile = os.path.join(self.directory, "pidfile")
        if not self.hypervisor.is_file(pidfile):
            return False
        return self.hypervisor.pid_exists(pidfile, "qemu")

    @property
    def address(self):  # TODO: this returns only the first IP
        for nic in self.spec["nics"]:
            if "br" not in nic:
                continue
            for lease in self.hypervisor.networks.get(nic["br"]).leases:
                if lease["mac"] == nic["mac"]:
                    return lease['ip']
        return None

    @property
    def vnc_uri(self):
        with self.monitor as monitor:
            vnc_data = monitor.execute("query-vnc")
        return f"vnc://:{self.spec['vnc']['password']}@{vnc_data['host']}:{vnc_data['service']}"

    def start(self):
        spec = self.spec
        for nic in spec["nics"]:
            if "br" not in nic:
                continue
            network = self.hypervisor.networks.get(nic['br'])
            if not network.is_running:
                network.start()
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
        self.hypervisor.remove_dir(self.directory)


class Vms:
    def __init__(self, hypervisor):
        self.hypervisor = hypervisor
        self.directory = os.path.join(hypervisor.directory, "vms")

    def __contains__(self, value):
        return self.hypervisor.is_dir(os.path.join(self.directory, value))

    def all(self):
        if not self.hypervisor.is_dir(self.directory):
            return []
        return [Vm(self.hypervisor, name) for name in self.hypervisor.list_dir(self.directory)]

    def get(self, name):
        if name not in self:
            raise Exception(f"Vm {name} does not exist")
        return Vm(self.hypervisor, name)

    def create(self, spec):
        if spec["name"] in self:
            raise Exception("Vm already exists")
        return Vm.create_from_spec(self.hypervisor, spec)

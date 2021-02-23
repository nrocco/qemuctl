import os
import uuid

from .utils import generate_mac


class Vm:
    def __init__(self, name, data, plan=None):
        self.name = name
        self.data = data
        self.plan = plan

    def create(self):
        self.plan.hypervisor.run(self.as_qemu_command())
        with self.plan.hypervisor.get_qmp(self) as qmp:
            qmp.execute("change-vnc-password", password=self.plan.hypervisor.vnc_password)
            qmp.execute("cont")

    def start(self):
        with self.plan.hypervisor.get_qmp(self) as qmp:
            qmp.execute("cont")

    def restart(self):
        with self.plan.hypervisor.get_qmp(self) as qmp:
            qmp.execute("system_reset")

    def stop(self):
        with self.plan.hypervisor.get_qmp(self) as qmp:
            qmp.execute("stop")

    def destroy(self):
        with self.plan.hypervisor.get_qmp(self) as qmp:
            qmp.execute("quit")
        self.plan.hypervisor.run(["rm", "-rf", os.path.join(self.plan.hypervisor.state_directory, self.name)])

    def info(self):
        with self.plan.hypervisor.get_qmp(self) as qmp:
            status = qmp.execute("query-status")
            vnc = qmp.execute("query-vnc")
        return {
            "status": status["status"],
            "display": "vnc://:{password}@{host}:{service}".format(**vnc, password=self.plan.hypervisor.vnc_password),
        }

    def as_qemu_command(self):
        state_dir = os.path.join(self.plan.hypervisor.state_directory, self.name)
        args = [
            "qemu-system-{}".format(self.data.get('arch', 'x86_64')),
            "-name", self.name,
            "-enable-kvm",
            "-daemonize",
            "-S",
            "-qmp", "unix:{},server,nowait".format(os.path.join(state_dir, 'qmp.sock')),
            "-m", str(self.data.get('memory', '1G')),
            "-uuid", str(uuid.uuid4()),
            "-vga", "std",
        ]
        if self.plan.hypervisor.vnc_address:
            args += "-display", f"vnc={self.plan.hypervisor.vnc_address}:0,to=100,password"
        else:
            args += "-display", "vnc=none"
        if 'smp' not in self.data:
            args += "-smp", "cores=2"
        elif isinstance(self.data['smp'], str):
            args += "-smp", self.data['smp']
        else:
            args += "-smp", ",".join(["{}={}".format(key, value) for key, value in self.data['smp'].items()])
        if 'smbios' in self.data:
            if isinstance(self.data['smbios'], str):
                args += "-smbios", self.data['smbios']
            else:
                args += "-smbios", ",".join(["{}={}".format(key, value) for key, value in self.data['smbios'].items()])
        if 'boot' in self.data:
            if isinstance(self.data['boot'], str):
                args += "-boot", self.data['boot']
            else:
                args += "-boot", ",".join(["{}={}".format(key, value) for key, value in self.data['boot'].items()])
        if 'cdrom' in self.data:
            args += "-cdrom", self.data['cdrom']
        for drive in self.data.get('drives', []):
            if isinstance(drive, str):
                args += "-drive", drive
            else:
                if 'file' in drive and not drive['file'].startswith('/'):
                    drive['file'] = os.path.join(state_dir, drive['file'])
                args += "-drive", ",".join(["{}={}".format(key, value) for key, value in drive.items()])
        for index, network in enumerate(self.data.get('networks', [])):
            if 'bridge' in network:
                args += "-netdev", "bridge,id=nic{},br={}".format(index, network['bridge'])

                args += "-device", "{},netdev=nic{},mac={}".format(network.get('type', 'virtio-net'), index, network.get('mac', generate_mac(f"{self.name}-{index}")))
        args += "-writeconfig", os.path.join(state_dir, 'config.cfg'),
        return args

    def __repr__(self):
        return f"<Vm {self.name}>"


class Plan:
    def __init__(self, data, hypervisor=None):
        self.hypervisor = hypervisor
        self.vms = [Vm(name, data, self) for name, data in data["vms"].items()]

    def __repr__(self):
        return f"<Plan vms:{len(self.vms)}>"

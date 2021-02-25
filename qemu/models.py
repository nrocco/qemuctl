import os
import uuid

from .utils import generate_mac


VM_DEFAULTS = {
    'arch': 'x86_64',
    'cpu': 'host',
    'memory': '1G',
    'vga': 'std',
    'smp': {
        'cores': 2,
    },
    'rtc': {
        'base': 'utc',
        'driftfix': 'slew',
    },
    'drives': [],
}

class Vm:
    def __init__(self, name, data, plan=None):
        self.name = name
        self.data = {**VM_DEFAULTS, **data}
        self.plan = plan

    def create(self):
        self.plan.hypervisor.run(["mkdir", "-p", os.path.join(self.plan.hypervisor.state_directory, self.name)])
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
            "qemu-system-{}".format(self.data['arch']),
            "-name", self.name,
            "-enable-kvm",
            "-daemonize",
            "-S",
            "-no-hpet",
            "-no-shutdown",
            "-qmp", "unix:{},server,nowait".format(os.path.join(state_dir, 'qmp.sock')),
            "-m", self.data['memory'],
            "-uuid", str(uuid.uuid4()),
            "-vga", self.data['vga'],
            "-cpu", self.data['cpu'],
            "-smp", ",".join(["{}={}".format(key, value) for key, value in self.data['smp'].items()]),
            "-rtc", ",".join(["{}={}".format(key, value) for key, value in self.data['rtc'].items()]),
            "-device", "virtio-tablet-pci",
            "-object", "secret,id=test,data=fuubar",
        ]
        if self.plan.hypervisor.vnc_address:
            args += "-display", f"vnc={self.plan.hypervisor.vnc_address}:0,to=100,password"
        if 'smbios' in self.data:
            args += "-smbios", ",".join(["{}={}".format(key, value) for key, value in self.data['smbios'].items()])
        if 'boot' in self.data:
            args += "-boot", ",".join(["{}={}".format(key, value) for key, value in self.data['boot'].items()])
        if 'cdrom' in self.data:
            args += "-cdrom", self.data['cdrom']
        for index, drive in enumerate(self.data['drives']):
            if 'file' in drive and not drive['file'].startswith('/'):
                drive['file'] = os.path.join(state_dir, drive['file'])
            drive['id'] = f"hd{index}"
            args += "-drive", ",".join(["{}={}".format(key, value) for key, value in drive.items()])
        for index, network in enumerate(self.data['networks']):
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

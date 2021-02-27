import json
import os

from .specs import Vm
from .qmp import Qmp
from .ssh import Ssh


class Hypervisor:
    def __init__(self, host, state_directory, vnc_address, vnc_password):
        self.host = host
        self.state_directory = state_directory
        self.vnc_address = vnc_address
        self.vnc_password = vnc_password

    def run(self, command, **kwargs):
        return Ssh(self.host, command, **kwargs)

    def get_qmp(self, name):
        return Qmp(self.host, os.path.join(self.state_directory, "vms", name, "qmp.sock"))

    def list_vms(self):
        result = self.run(["ls", os.path.join(self.state_directory, "vms")])
        return result.stdout.splitlines()

    def default_opts_for_vm(self, name):
        chroot = os.path.join(self.state_directory, "vms", name)
        return {
            "chroot": chroot,
            "pidfile": os.path.join(chroot, "pidfile"),
            "writeconfig": os.path.join(chroot, "config.cfg"),
            "qmp": f"unix:{chroot}/qmp.sock,server=yes,wait=no",
            "vnc": {
                "vnc": self.vnc_address,
                "password": self.vnc_password,
            },
        }

    def create_vm(self, spec):
        # TODO check if vm is not already created,
        self.run(["mkdir", "-p", spec["chroot"]])
        self.run(["tee", os.path.join(spec["chroot"], "spec.json")], input=json.dumps(spec, indent=2))
        self.run([f"qemu-system-{spec['arch']}"] + spec.to_args())
        with self.get_qmp(spec["name"]) as qmp:
            if spec["vnc"]["password"]:
                qmp.execute("change-vnc-password", password=spec["vnc"]["password"])
            qmp.execute("cont")

    def get_vm(self, name):
        spec = self.run(["cat", os.path.join(self.state_directory, "vms", name, "spec.json")]).stdout
        return Vm(json.loads(spec))

    def remove_vm(self, vm):
        # TODO check if vm is running
        with self.get_qmp(vm) as qmp:
            qmp.execute("quit")
        self.run(["rm", "-rf", os.path.join(self.state_directory, "vms", vm)])

    def list_images(self):
        result = self.run(["ls", "-lh", os.path.join(self.state_directory, "images")])
        return result.stdout.splitlines()

    def get_image(self, image):
        result = self.run(["qemu-img", "info", "--backing-chain", "--output=json", os.path.join(self.state_directory, "images", image)])
        return json.loads(result.stdout)

    def remove_image(self, image):
        self.run(["rm", os.path.join(self.state_directory, "images", image)])

    def get_leases(self, network):
        leases = []
        result = self.run(["cat", os.path.join(self.state_directory, "networks", network, f"{network}.leases")])
        for line in result.stdout.splitlines():
            data = line.split(" ")
            leases.append({
                "timestamp": data[0],
                "mac": data[1],
                "ip": data[2],
                "host": data[3],
                "id": data[4],
            })
        return leases

    def start_network(self, network):
        conf_file = os.path.join(self.state_directory, "networks", network, f"{network}.conf")
        self.run(["dnsmasq", f"--conf-file={conf_file}"])

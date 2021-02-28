import json
import os
import subprocess

from .dnsmasq import get_dnsmasq_config
from .qmp import Qmp
from .specs import Vm
from .ssh import Ssh


class Hypervisor:
    def __init__(self, host, state_directory, vnc_address=None, vnc_password=None):
        self.host = host
        self.state_directory = state_directory
        self.vnc_address = vnc_address
        self.vnc_password = vnc_password

    def run(self, command, **kwargs):
        return Ssh(self.host, command, **kwargs)

    def get_qmp(self, name):
        return Qmp(self.host, self.get_vms_dir(name, "qmp.sock"))

    def get_vms_dir(self, *name):
        return os.path.join(self.state_directory, "vms", *name)

    def get_images_dir(self, *name):
        return os.path.join(self.state_directory, "images", *name)

    def get_networks_dir(self, *name):
        return os.path.join(self.state_directory, "networks", *name)

    def list_vms(self, details=False):
        return self.run(["ls", "-lh1" if details else "-h1", self.get_vms_dir()]).stdout.splitlines()

    def list_images(self, details=False):
        return self.run(["ls", "-lh1" if details else "-h1", self.get_images_dir()]).stdout.splitlines()

    def list_networks(self, details=False):
        return self.run(["ls", "-lh1" if details else "-h1", self.get_networks_dir()]).stdout.splitlines()

    def default_opts_for_vm(self, name):
        return {
            "chroot": self.get_vms_dir(name),
            "pidfile": self.get_vms_dir(name, "pidfile"),
            "qmp": f"unix:{self.get_vms_dir(name, 'qmp.sock')},server=yes,wait=no",
            "vnc": {
                "vnc": self.vnc_address,
                "password": self.vnc_password,
            },
            "writeconfig": self.get_vms_dir(name, "config.cfg"),
        }

    def create_vm(self, spec):
        # TODO check if vm is not already created,
        self.run(["mkdir", "-p", spec["chroot"]])
        self.run(["tee", self.get_vms_dir(spec["name"], "spec.json")], input=json.dumps(spec, indent=2))
        for drive in spec["drives"]:
            try:
                self.run(["test", "-f", drive["file"]])
                continue
            except:
                pass
            if "size" not in drive and "backing_file" not in drive:
                continue
            args = ["qemu-img", "create"]
            if "backing_file" in drive and "format" in drive:
                args += "-F", drive["format"]
            if "backing_file" in drive:
                args += "-b", drive["backing_file"]
            if "format" in drive:
                args += "-f", drive["format"]
            args += [drive["file"]]
            if "size" in drive:
                args += [drive["size"]]
            self.run(args)
        self.run([f"qemu-system-{spec['arch']}"] + spec.to_args())
        with self.get_qmp(spec["name"]) as qmp:
            if spec["vnc"]["password"]:
                qmp.execute("change-vnc-password", password=spec["vnc"]["password"])
            qmp.execute("cont")
            vnc = qmp.execute("query-vnc")
        return vnc

    def get_vm(self, name):
        spec = self.run(["cat", self.get_vms_dir(name, "spec.json")]).stdout
        return Vm(json.loads(spec))

    def destroy_vm(self, name):
        # TODO check if name is running
        with self.get_qmp(name) as qmp:
            qmp.execute("quit")
        self.run(["rm", "-rf", self.get_vms_dir(name)])

    def get_image(self, image):
        result = self.run(["qemu-img", "info", "--backing-chain", "--output=json", self.get_images_dir(image)])
        return json.loads(result.stdout)

    def delete_image(self, image):
        self.run(["rm", self.get_images_dir(image)])

    def get_leases(self, network):
        leases = []
        result = self.run(["cat", self.get_networks_dir(network, "leases")])
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

    def create_network(self, name, dhcp=False, ip_range=None):
        self.run(["mkdir", self.get_networks_dir(name)])
        self.run(["ip", "link", "add", "dev", name, "type", "bridge", "stp_state", "1"])
        if ip_range:
            self.run(["ip", "addr", "add", str(ip_range[1]), "dev", name])
        if dhcp:
            dnsmasq_conf = get_dnsmasq_config(name, self.get_networks_dir(name), ip_range)
            self.run(["tee", self.get_networks_dir(name, "dnsmasq.conf")], input=dnsmasq_conf)
            conf_file = self.get_networks_dir(name, "dnsmasq.conf")
            self.run(["dnsmasq", f"--conf-file={conf_file}"])

    def destroy_network(self, name):
        try:
            self.run(["pkill", "--pidfile", self.get_networks_dir(name, 'pidfile')])
        except subprocess.CalledProcessError:
            pass
        try:
            self.run(["ip", "link", "delete", name])
        except subprocess.CalledProcessError:
            pass
        self.run(["rm", "-rf", self.get_networks_dir(name)])

import json
import os

from .ssh import Qmp
from .ssh import Ssh


class Hypervisor:
    def __init__(self, host, state_directory, vnc_address, vnc_password):
        self.host = host
        self.state_directory = state_directory
        self.vnc_address = vnc_address
        self.vnc_password = vnc_password

    def run(self, command):
        return Ssh(self.host, command)

    def get_qmp(self, vm):
        return Qmp(self.host, os.path.join(self.state_directory, vm.name, "qmp.sock"))

    def images_list(self):
        result = self.run(["ls", "-lh", os.path.join(self.state_directory, 'images')])
        return result.stdout.splitlines()

    def images_get(self, image):
        result = self.run(["qemu-img", "info", "--backing-chain", "--output=json", os.path.join(self.state_directory, 'images', image)])
        return json.loads(result.stdout)

    def images_remove(self, image):
        self.run(["rm", os.path.join(self.state_directory, 'images', image)])

    def get_network_leases(self, bridge):
        leases = []
        result = self.run(["cat", os.path.join(self.state_directory, f"{bridge}.leases")])
        for line in json.loads(result.stdout).splitlines():
            data = line.split(" ")
            leases.append({
                'timestamp': data[0],
                'mac': data[1],
                'ip': data[2],
                'host': data[3],
                'id': data[4],
            })
        return leases

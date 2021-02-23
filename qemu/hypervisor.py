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

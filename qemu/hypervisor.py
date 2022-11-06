import os
import shutil
import subprocess

from .qmp import Qmp
from .images import Images
from .networks import Networks
from .vms import Vms


class Hypervisor:
    def __init__(self, directory="", vnc_address="127.0.0.1", vnc_password=None):
        self.directory = os.path.abspath(directory)
        self.vms = Vms(self)
        self.images = Images(self)
        self.networks = Networks(self)
        self.config = {
            'vnc': {
                'address': vnc_address,
                'password': vnc_password,
            },
            'uefi': {
                'code': '/usr/share/OVMF/OVMF_CODE.fd',  # TODO this is hard coded
                'vars': '/usr/share/OVMF/OVMF_VARS.fd',  # TODO this is hard coded
            },
        }

    def exec(self, command, check=True, cwd=None):
        return subprocess.run(command, text=True, capture_output=True, check=check, cwd=cwd).stdout

    def pid_kill(self, pidfile, name=None):
        args = ["pkill", "--pidfile", pidfile]
        if name:
            args += [name]
        return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def pid_exists(self, pidfile, name=None):
        args = ["pgrep", "--pidfile", pidfile]
        if name:
            args += [name]
        return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def open_file(self, filename, *args):
        return open(filename, *args)

    def symlink(self, source, destination):
        return os.link(source, destination)

    def list_dir(self, directory):
        return os.listdir(directory)

    def make_dir(self, directory):
        return os.makedirs(directory)

    def is_file(self, filename):
        return os.path.isfile(filename)

    def is_dir(self, directory):
        return os.path.isdir(directory)

    def remove_file(self, filename):
        return os.remove(filename)

    def remove_dir(self, directory):
        return shutil.rmtree(directory)

    def walk(self, directory):
        files = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                files.append(os.path.join(root, file))
        return files

    def qmp(self, filename):
        return Qmp(filename)

import os
import subprocess

from .images import Images
from .networks import Networks
from .vms import Vms


class Hypervisor:
    def __init__(self, directory):
        self.directory = os.path.abspath(directory)
        self.vms = Vms(self)
        self.images = Images(self)
        self.networks = Networks(self)
        self.config = {
            'vnc': {
                'address': os.environ.get("QEMUCTL_VNC_ADDRESS", "127.0.0.1"),
                'password': os.environ.get("QEMUCTL_VNC_PASSWORD", None),
            },
        }

    def exec(self, command, text=True, capture_output=True, check=True, cwd=None):
        return subprocess.run(command, text=text, capture_output=capture_output, check=check, cwd=cwd)

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

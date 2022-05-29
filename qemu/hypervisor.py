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

    def exec(self, command, text=True, capture_output=True, check=True):
        return subprocess.run(command, text=text, capture_output=capture_output, check=check)

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

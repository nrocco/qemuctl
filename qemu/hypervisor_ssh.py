import os
import paramiko
import shlex

from stat import S_ISDIR
from stat import S_ISREG
from urllib.parse import urlparse

from .qmp_ssh import QmpSSH
from .hypervisor import Hypervisor


class HypervisorSSH(Hypervisor):
    def __init__(self, host, vnc_address="127.0.0.1", vnc_password=None):
        self._host = urlparse(host)
        if self._host.scheme != 'ssh':
            raise Exception()
        self._client = None
        self._sftp = None
        super().__init__(self._host.path, vnc_address, vnc_password)

    @property
    def client(self):
        if not self._client:
            self._client = paramiko.SSHClient()
            self._client.load_system_host_keys()
            self._client.connect(self._host.hostname, username=self._host.username, password=self._host.password)
        return self._client

    @property
    def sftp(self):
        if not self._sftp:
            self._sftp = self.client.open_sftp()
        return self._sftp

    def exec(self, command, check=True, cwd=None):
        cwd = cwd or self.directory
        stdin, stdout, stderr = self.client.exec_command(f"cd {cwd}; " + shlex.join(command))
        resultcode = stdout.channel.recv_exit_status()
        if check and resultcode > 0:
            raise Exception(stderr.read().decode())
        return stdout.read().decode()

    def pid_kill(self, pidfile, name=None):
        args = ["pkill", "--pidfile", pidfile]
        if name:
            args += [name]
        stdin, stdout, stderr = self.client.exec_command(shlex.join(args))
        return stdout.channel.recv_exit_status() == 0

    def pid_exists(self, pidfile, name=None):
        args = ["pgrep", "--pidfile", pidfile]
        if name:
            args += [name]
        stdin, stdout, stderr = self.client.exec_command(shlex.join(args))
        return stdout.channel.recv_exit_status() == 0

    def open_file(self, filename, *args):
        return self.sftp.file(filename, *args)

    def symlink(self, source, destination):
        return self.sftp.symlink(source, destination)

    def list_dir(self, directory):
        return self.sftp.listdir(directory)

    def make_dir(self, directory):
        parent = os.path.dirname(directory)
        if not self.is_dir(parent):
            self.make_dir(parent)
        return self.sftp.mkdir(directory)

    def is_file(self, filename):
        try:
            return S_ISREG(self.sftp.stat(filename).st_mode)
        except FileNotFoundError:
            return False

    def is_dir(self, directory):
        try:
            return S_ISDIR(self.sftp.stat(directory).st_mode)
        except FileNotFoundError:
            return False

    def remove_file(self, filename):
        return self.sftp.remove(filename)

    def remove_dir(self, directory):
        if not self.is_dir(directory):
            raise Exception(f"{directory} is not a directory")
        self.client.exec_command(f"rm -rf {shlex.quote(directory)}")

    def walk(self, directory):
        return self.exec(["find", directory, "-type", "f"]).split()

    def qmp(self, filename):
        channel = self.client.get_transport().open_session()
        channel.exec_command(f"socat - UNIX-CONNECT:{filename}")
        return QmpSSH(channel)

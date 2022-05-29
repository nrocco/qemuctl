from qemu.hypervisor import Hypervisor
from unittest.mock import patch


def test_hypervisor():
    h = Hypervisor("/tmp")
    assert h.directory == "/tmp"


@patch("subprocess.run")
def test_hypervisor_exec(mock_run):
    h = Hypervisor("/tmp")
    h.exec(["test"])
    h.pid_kill("pidfile")
    h.pid_kill("pidfile", "qemu")
    h.pid_exists("pidfile")
    h.pid_exists("pidfile", "qemu")

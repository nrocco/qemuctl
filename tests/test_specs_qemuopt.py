from qemu.specs import DriveOpt
from qemu.specs import NicOpt
from qemu.specs import QemuOpt
from qemu.specs import VncOpt


def test_qemuopt_from_string():
    opt = QemuOpt("smbios", "type=1,serial=fuu0123")
    assert opt.key == "smbios"
    assert opt == {"type": "1", "serial": "fuu0123"}
    assert opt.to_args() == ("--smbios", "type=1,serial=fuu0123")


def test_qemuopt_from_dict():
    opt = QemuOpt("smbios", {"type": 1, "serial": "fuu0123"})
    assert opt.key == "smbios"
    assert opt == {"type": 1, "serial": "fuu0123"}
    assert opt.to_args() == ("--smbios", "type=1,serial=fuu0123")


def test_qemuopt_from_kwargs():
    opt = QemuOpt("smbios", type=1, serial="fuu0123")
    assert opt.key == "smbios"
    assert opt == {"type": 1, "serial": "fuu0123"}
    assert opt.to_args() == ("--smbios", "type=1,serial=fuu0123")


def test_qemuopt_from_string_nokey():
    data_provider = (
        ("accel", "kvm", {"accel": "kvm"}, ("--accel", "accel=kvm")),
        ("cdrom", "fuubar.iso", {"file": "fuubar.iso"}, ("--cdrom", "file=fuubar.iso")),
        ("machine", "kvm", {"type": "kvm"}, ("--machine", "type=kvm")),
        ("memory", "2G", {"size": "2G"}, ("--m", "size=2G")),
        ("smp", "2", {"cpus": "2"}, ("--smp", "cpus=2")),
        ("vnc", "127.0.0.2:0", {"vnc": "127.0.0.2:0"}, ("--vnc", "vnc=127.0.0.2:0")),
    )
    for key, value, expected_dict, expected_args in data_provider:
        opt = QemuOpt(key, value)
        assert opt.key == key
        assert opt == expected_dict
        assert opt.to_args() == expected_args


def test_qemuopt_vnc():
    opt = VncOpt("vnc=127.0.0.1,to=100,password=aabcd")
    assert opt.key == "vnc"
    assert opt == {"vnc": "127.0.0.1:0", "to": "100", "password": "aabcd"}
    assert opt.to_args() == ("--vnc", "vnc=127.0.0.1:0,to=100,password=yes")


def test_qemuopt_nic():
    opt = NicOpt("br0")
    assert opt.key == "nic"
    assert opt == {"br": "br0", "type": "bridge", "model": "virtio-net-pci", "mac": opt["mac"]}
    assert opt.to_args() == ("--nic", f"br=br0,type=bridge,model=virtio-net-pci,mac={opt['mac']}")


def test_qemuopt_nic_none():
    opt = NicOpt("type=none,id=nic0")
    assert opt.key == "nic"
    assert opt == {"type": "none"}
    assert opt.to_args() == ("--nic", "type=none")


def test_qemuopt_drive():
    opt = DriveOpt({"file": "test.qcow2", "size": "20G"})
    assert opt.key == "drive"
    assert opt == {"file": "test.qcow2", "size": "20G", "if": "virtio", "format": "qcow2"}
    assert opt.to_args() == ("--drive", "file=test.qcow2,if=virtio,format=qcow2")

    opt = DriveOpt({"file": "test.raw", "size": "20G"})
    assert opt.key == "drive"
    assert opt == {"file": "test.raw", "size": "20G", "if": "virtio", "format": "raw"}
    assert opt.to_args() == ("--drive", "file=test.raw,if=virtio,format=raw")


def test_qemuopt_drive_only_backing_file():
    opt = DriveOpt("backing_file=/fuu/bar/test.qcow2,chroot=/fuu")
    assert opt.key == "drive"
    assert opt == {"file": "/fuu/disk.qcow2", "backing_file": "/fuu/bar/test.qcow2", "chroot": "/fuu", "if": "virtio", "format": "qcow2"}
    assert opt.to_args() == ("--drive", "if=virtio,file=/fuu/disk.qcow2,format=qcow2")


def test_qemuopt_drive_format():
    opt = DriveOpt({"file": "test.img", "size": "20G", "format": "qcow2"})
    assert opt.key == "drive"
    assert opt == {"file": "test.img", "size": "20G", "if": "virtio", "format": "qcow2"}
    assert opt.to_args() == ("--drive", "file=test.img,format=qcow2,if=virtio")

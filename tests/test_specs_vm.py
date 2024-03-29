import json

from qemu.specs import VmSpec


def test_vm_from_dict():
    vm = VmSpec({
        "name": "test-vm",
        "chroot": "/fuu",
        "boot": {
            "order": "nd",
        },
        "fuu": None,
        "drives": [
            "disk01.qcow2,size=50G",
        ],
        "cdrom": "bar/cdrom.iso",
        "vnc": "127.0.0.1",
    })
    assert vm["arch"] == "x86_64"
    assert "fuu" not in vm
    assert "50G" == vm["drives"][0]["size"]
    assert vm.to_qemu_args() == [
        "qemu-system-x86_64",
        "--enable-kvm",
        "--daemonize",
        "--nodefaults",
        "--no-hpet",
        "--no-shutdown",
        "--S",
        "--chroot", "/fuu",
        "--uuid", vm["uuid"],
        "--cpu", "host",
        "--vga", "std",
        "--device", "driver=virtio-tablet-pci",
        "--device", "driver=virtio-balloon-pci",
        "--device", "driver=virtio-rng-pci",
        "--drive", "id=hd0,file=disk01.qcow2,if=virtio,format=qcow2",
        "--name", "test-vm",
        "--boot", "order=nd",
        "--cdrom", "bar/cdrom.iso",
        "--vnc", "vnc=127.0.0.1:0",
    ]


def test_vm_with_kvm_disabled():
    vm = VmSpec(kvm=False)
    assert False is vm["kvm"]
    assert "--enable-kvm" not in vm.to_qemu_args()


def test_vm_with_uefi_boot():
    vm = VmSpec(uefi=True)
    assert "OVMF_CODE.fd" == vm["drives"][0]["file"]
    assert "OVMF_VARS.fd" == vm["drives"][1]["file"]
    assert "if=pflash,format=raw,readonly=on,file=OVMF_CODE.fd" in vm.to_qemu_args()
    assert "if=pflash,format=raw,file=OVMF_VARS.fd" in vm.to_qemu_args()


def test_vm_with_shutdown_enabled():
    vm = VmSpec(shutdown=True)
    assert True is vm["shutdown"]
    assert "--no-shutdown" not in vm.to_qemu_args()


def test_vm_with_uuid_from_input():
    vm = VmSpec(uuid="252f489b-d5e3-45e0-ab3e-3745b569fc53")
    assert "252f489b-d5e3-45e0-ab3e-3745b569fc53" == vm["uuid"]
    assert "252f489b-d5e3-45e0-ab3e-3745b569fc53" in vm.to_qemu_args()


def test_vm_from_string():
    vm = VmSpec({"boot": "order=n"})
    assert vm["boot"] == {"order": "n"}
    assert "order=n" in vm.to_qemu_args()


def test_vm_serialize_and_restore():
    vm1 = VmSpec({
        "name": "test-vm",
        "chroot": "/fuu",
        "boot": "order=nd",
        "drives": ["disk01.qcow2,size=50G"],
        "nics": ["br0,mac=aa:bb:cc:dd:ee:ff,model=virtio-net-pci"],
        "vnc": "127.0.0.1,password=fuubar",
    })
    vm2 = VmSpec(json.loads(json.dumps(vm1)))
    assert vm1["name"] == vm2["name"] == "test-vm"
    assert vm1["uuid"] == vm2["uuid"]
    assert vm1["chroot"] == vm2["chroot"] == "/fuu"
    assert vm1["boot"] == vm2["boot"] == {"order": "nd"}
    assert vm1["vnc"] == vm2["vnc"] == {"password": "fuubar", "vnc": "127.0.0.1:0"}
    assert vm1["drives"] == vm2["drives"] == [{"id": "hd0", "file": "disk01.qcow2", "format": "qcow2", "size": "50G", "if": "virtio"}]
    assert vm1["nics"] == vm2["nics"] == [{"id": "nic0", "br": "br0", "mac": "aa:bb:cc:dd:ee:ff", "model": "virtio-net-pci", "type": "bridge"}]
    assert json.dumps(vm1) == json.dumps(vm2)

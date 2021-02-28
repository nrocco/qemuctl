import json

from qemu.specs import Vm


def test_vm_from_dict():
    vm = Vm({
        "name": "test-vm",
        "chroot": "/fuu",
        "boot": {
            "order": "nd",
        },
        "fuu": None,
        "drives": [
            "disk01.qcow2,size=50G",
        ],
        "vnc": "127.0.0.1",
    })
    assert vm["arch"] == "x86_64"
    assert "fuu" not in vm
    assert "50G" == vm["drives"][0]["size"]
    assert vm.to_args() == [
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
        '--device', 'driver=virtio-balloon-pci',
        "--drive", "id=hd0,file=/fuu/disk01.qcow2,if=virtio,format=qcow2",
        "--name", "test-vm",
        "--boot", "order=nd",
        "--vnc", "vnc=127.0.0.1:0",
    ]


def test_vm_with_kvm_disabled():
    vm = Vm(kvm=False)
    assert False is vm["kvm"]
    assert "--enable-kvm" not in vm.to_args()


def test_vm_with_shutdown_enabled():
    vm = Vm(shutdown=True)
    assert True is vm["shutdown"]
    assert "--no-shutdown" not in vm.to_args()


def test_vm_with_uuid_from_input():
    vm = Vm(uuid="252f489b-d5e3-45e0-ab3e-3745b569fc53")
    assert "252f489b-d5e3-45e0-ab3e-3745b569fc53" == vm["uuid"]
    assert "252f489b-d5e3-45e0-ab3e-3745b569fc53" in vm.to_args()


def test_vm_from_string():
    vm = Vm({"boot": "order=n"})
    assert vm["boot"] == {"order": "n"}
    assert "order=n" in vm.to_args()


def test_vm_serialize_and_restore():
    vm1 = Vm({
        "name": "test-vm",
        "chroot": "/fuu",
        "boot": "order=nd",
        "drives": ["disk01.qcow2,size=50G"],
        "nics": ["br0,mac=aa:bb:cc:dd:ee:ff,model=virtio-net-pci"],
        "vnc": "127.0.0.1,password=fuubar",
    })
    vm2 = Vm(json.loads(json.dumps(vm1)))
    assert vm1["name"] == vm2["name"] == "test-vm"
    assert vm1["uuid"] == vm2["uuid"]
    assert vm1["chroot"] == vm2["chroot"] == "/fuu"
    assert vm1["boot"] == vm2["boot"] == {"order": "nd"}
    assert vm1["vnc"] == vm2["vnc"] == {"password": "fuubar", "vnc": "127.0.0.1:0"}
    assert vm1["drives"] == vm2["drives"] == [{"id": "hd0", "chroot": "/fuu", "file": "/fuu/disk01.qcow2", "format": "qcow2", "size": "50G", "if": "virtio"}]
    assert vm1["nics"] == vm2["nics"] == [{"id": "nic0", "br": "br0", "mac": "aa:bb:cc:dd:ee:ff", "model": "virtio-net-pci", "type": "bridge"}]
    assert json.dumps(vm1) == json.dumps(vm2)

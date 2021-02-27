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
        "--uuid", vm["uuid"],
        "--cpu", "host",
        "--vga", "std",
        "--device", "driver=virtio-tablet-pci",
        "--drive", "id=hd0,file=/fuu/disk01.qcow2,if=virtio",
        "--name", "test-vm",
        "--chroot", "/fuu",
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

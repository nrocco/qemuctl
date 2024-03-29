import ipaddress
import os
import random
import uuid


QEMU_BOOL_OPTS = [
    "daemonize",
    "defaults",
    "hpet",
    "kvm",
    "reboot",
    "shutdown",
    "snapshot",
    "startup",
]

QEMU_PLAIN_OPTS = [
    "arch",
    "cdrom",
    "chroot",
    "cpu",
    "monitor",
    "name",
    "pidfile",
    "qmp",  # TODO this should be a complex opt
    "runas",
    "uuid",
    "vga",
]

QEMU_COMPLEX_OPTS = [
    "accel",
    "boot",
    "drive",
    "machine",
    "memory",
    "rtc",
    "smbios",
    "smp",
    "vnc",
]

QEMU_LIST_OPTS = [
    "blockdevs",
    "chardevs",
    "devices",
    "drives",
    "netdevs",
    "nics",
]


class VmSpec(dict):
    def __init__(self, *args, **kwargs):
        defaults = {
            "arch": "x86_64",
            "kvm": True,
            "daemonize": True,
            "defaults": False,
            "shutdown": False,
            "snapshot": False,
            "startup": False,
            "chroot": None,
            "uuid": str(uuid.uuid4()),
            "cpu": "host",
            "vga": "std",
            "devices": [],
            "drives": [],
            "nics": [],
        }
        for arg in args:
            defaults.update(arg)
        defaults.update(kwargs)
        if not defaults['machine']:
            defaults["machine"] = "pc" if defaults["arch"] == "x86_64" else "virt"
        spec = {}
        for key, value in defaults.items():
            if value is None:
                continue
            elif key in QEMU_PLAIN_OPTS:
                spec[key] = value
            elif key in QEMU_BOOL_OPTS and type(value) == bool:
                spec[key] = value
            elif key == "vnc":
                spec[key] = value if isinstance(value, VncOpt) else VncOpt(value)
            elif key in QEMU_COMPLEX_OPTS:
                spec[key] = value if isinstance(value, QemuOpt) else QemuOpt(key, value)
            elif key == "nics":
                spec[key] = [NicOpt({"id": f"nic{index}"}, nic) for index, nic in enumerate(value)]
            elif key == "uefi" and value:
                spec['drives'].append(DriveOpt("if=pflash,format=raw,readonly=on,file=uefi_code.fd"))
                spec['drives'].append(DriveOpt("if=pflash,format=raw,file=uefi_vars.fd"))
            elif key == "drives":
                spec[key] = [DriveOpt({"id": f"hd{index}"}, drive) for index, drive in enumerate(value)]
            elif key in QEMU_LIST_OPTS:
                if key not in spec:
                    spec[key] = []
                spec[key] += [QemuOpt(key.rstrip("s"), opt) for opt in value]
        if not [device for device in spec["devices"] if device["driver"] == "virtio-tablet-pci"]:
            spec["devices"] += [QemuOpt("device", driver="virtio-tablet-pci")]
        if not [device for device in spec["devices"] if device["driver"] == "virtio-balloon-pci"]:
            spec["devices"] += [QemuOpt("device", driver="virtio-balloon-pci")]
        if not [device for device in spec["devices"] if device["driver"] == "virtio-rng-pci"]:
            spec["devices"] += [QemuOpt("device", driver="virtio-rng-pci")]
        super().__init__(spec)

    def to_qemu_args(self):
        args = [f"qemu-system-{self['arch']}"]
        for key, value in self.items():
            if key == "arch":
                continue
            elif isinstance(value, QemuOpt):
                args += value.to_qemu_args()
            elif key == "startup" and value is False:
                args += ["--S"]
            elif key == "kvm" and value is True:
                args += ["--enable-kvm"]
            elif key == "daemonize" and value is True:
                args += ["--daemonize"]
            elif key == "defaults" and value is False:
                args += ["--nodefaults"]
            elif key in ["hpet", "shutdown"] and value is False:
                args += [f"--no-{key}"]
            elif key in QEMU_PLAIN_OPTS:
                args += f"--{key}", value
            elif key in QEMU_LIST_OPTS:
                for opt in value:
                    args += opt.to_qemu_args()
        return args


class QemuOpt(dict):
    non_qemu_opts = []

    def __init__(self, key, *args, **kwargs):
        self.key = key
        spec = {}
        for arg in args:
            if type(arg) == dict:
                spec.update(arg)
            elif type(arg) == str:
                if "=" not in arg.split(",")[0]:
                    if key == "smp":
                        arg = f"cpus={arg}"
                    elif key == "machine":
                        arg = f"type={arg}"
                    elif key == "accel":
                        arg = f"accel={arg}"
                    elif key == "memory":
                        arg = f"size={arg}"
                    elif key == "nic":
                        arg = f"br={arg}"
                    elif key == "drive":
                        arg = f"file={arg}"
                    elif key == "vnc":
                        arg = f"vnc={arg}"
                spec.update({key: val for key, val in [opt.split("=") for opt in arg.split(",")]})
        spec.update(kwargs)
        super().__init__(spec)

    def to_qemu_args(self):
        return (f"--{'m' if 'memory' == self.key else self.key}", ",".join([f"{key}={value}" for key, value in self.items() if key not in self.non_qemu_opts]))


class VncOpt(QemuOpt):
    non_qemu_opts = ["password"]

    def __init__(self, *args, **kwargs):
        super().__init__("vnc", *args, **kwargs)
        if ":" not in self["vnc"]:
            self["vnc"] += ":0"

    def to_qemu_args(self):
        key, value = super().to_qemu_args()
        if "password" in self:
            value += ",password=yes"
        return (key, value)


class NicOpt(QemuOpt):
    def __init__(self, *args, **kwargs):
        super().__init__("nic", *args, **kwargs)
        if "type" in self and self["type"] == "none":
            del self["id"]
            return
        if "br" in self and "type" not in self:
            self["type"] = "bridge"
        if "model" not in self:
            self["model"] = "virtio-net-pci"
        if "mac" not in self:
            self["mac"] = "52:54:" + ":".join("%02x" % random.randint(0, 255) for x in range(4))


class DriveOpt(QemuOpt):
    non_qemu_opts = ["size", "backing_file"]

    def __init__(self, *args, **kwargs):
        super().__init__("drive", *args, **kwargs)
        if "if" not in self:
            self["if"] = "virtio"
        if "file" not in self:
            ext = ".qcow2" if "backing_file" not in self else os.path.splitext(self["backing_file"])[1]
            self["file"] = f"{self['id'] if 'id' in self else 'disk'}{ext}"
        if "format" not in self:
            if self["file"].endswith(".qcow2"):
                self["format"] = "qcow2"
            else:
                self["format"] = "raw"

    def to_qemu_img_args(self):
        args = ["qemu-img", "create"]
        if "backing_file" in self and "format" in self:
            args += "-F", self["format"]
        if "backing_file" in self:
            args += "-b", self["backing_file"]
        if "format" in self:
            args += "-f", self["format"]
        args += [self["file"]]
        if "size" in self:
            args += [self["size"]]
        return args


class NetworkSpec(dict):
    def __init__(self, *args, **kwargs):
        spec = {
            "dhcp": False,
            "dns": False,
            "tftp": False,
            "ip_range": None,
        }
        for arg in args:
            spec.update(arg)
        spec.update(kwargs)
        if not spec["ip_range"] and (spec['dhcp'] or spec['dns'] or spec['tftp']):
            raise Exception("A network without an ip_range cannot have services")
        if spec["ip_range"]:
            self.ip_range = ipaddress.ip_network(spec["ip_range"])
        else:
            self.ip_range = None
        super().__init__(spec)

import uuid
import random


class Vm(dict):
    def __init__(self, args={}, **kwargs):
        spec = {
            'arch': 'x86_64',
            'kvm': True,
            'hpet': False,
            'shutdown': False,
            'uuid': str(uuid.uuid4()),
            'vga': 'std',
            'cpu': 'host',
        }
        spec.update(args)
        spec.update(kwargs)
        spec.update({
            'devices': [QemuOpt(device) for device in spec['devices']],
            'networks': [Network({'id': f"nic{index}", **network}) for index, network in enumerate(spec['networks'])],
            'drives': [Drive({'id': f"hd{index}", **drive}) for index, drive in enumerate(spec['drives'])],
        })
        spec['devices'].append(QemuOpt(driver='virtio-tablet-pci'))
        super().__init__(spec)


class QemuOpt(dict):
    def __init__(self, args={}, **kwargs):
        args.update(kwargs)
        super().__init__(args)


class Network(dict):
    def __init__(self, args={}, **kwargs):
        spec = {
            'type': 'bridge',
            'driver': 'virtio-net',
        }
        spec.update(args)
        spec.update(kwargs)
        if 'bridge' not in spec:
            raise RuntimeError("Network missing required bridge= option")
        if 'mac' not in spec:
            spec['mac'] = '52:54:' + ':'.join('%02x' % random.randint(0, 255) for x in range(4))
        super().__init__(spec)


class Drive(dict):
    def __init__(self, args={}, **kwargs):
        spec = {
            'if': 'virtio',
        }
        spec.update(args)
        spec.update(kwargs)
        super().__init__(spec)

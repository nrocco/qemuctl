import zlib


def generate_mac(name):
    crc = zlib.crc32(f"{name}".encode("utf-8")) & 0xffffffff
    crc = str(hex(crc))[2:]

    return "52:54:%s%s:%s%s:%s%s:%s%s" % tuple(crc)


def qemu_arg_to_dict(value):
    return {key: value for key, value in [opt.split('=') for opt in value.split(',')]}


def dict_to_qemu_arg(value):
    return ",".join([f"{key}={value}" for key, value in value.items()])

import zlib


def generate_mac(name):
    crc = zlib.crc32(f"{name}".encode("utf-8")) & 0xffffffff
    crc = str(hex(crc))[2:]

    return "52:54:%s%s:%s%s:%s%s:%s%s" % tuple(crc)

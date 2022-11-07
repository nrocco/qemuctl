import binascii
import json
import logging
import os
import socket


class SocketConnection:
    def __init__(self, path):
        self.path = path
        self.socket = None

    def is_open(self):
        return self.socket is not None

    def open(self):
        if not self.socket:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.path)

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def read(self, size):
        return os.read(self.socket.fileno(), size)

    def write(self, data):
        os.write(self.socket.fileno(), data.encode())


class SSHConnection:
    def __init__(self, channel):
        self.channel = channel

    def is_open(self):
        return not self.channel.closed

    def open(self):
        pass

    def close(self):
        self.channel.close()

    def read(self, size):
        return self.channel.recv(size)

    def write(self, data):
        self.channel.send(data)


class Qmp:
    """
    https://github.com/qemu/qemu/blob/master/docs/interop/qmp-spec.txt
    https://qemu.readthedocs.io/en/latest/interop/qemu-qmp-ref.html
    https://qemu.readthedocs.io/en/latest/system/monitor.html
    https://gist.github.com/rgl/dc38c6875a53469fdebb2e9c0a220c6c
    """
    @classmethod
    def from_local_socket(cls, path):
        return cls(SocketConnection(path))

    @classmethod
    def from_ssh_channel(cls, channel):
        return cls(SSHConnection(channel))

    def __init__(self, conn):
        self.events = []
        self.conn = conn

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        self.events = []
        self.conn.open()
        if len(list(self._read())) == 0:
            raise RuntimeError("Qmp monitor not available")
        self.execute("qmp_capabilities", enable=["oob"])

    def close(self):
        logging.debug(">>> EOF")
        self.conn.close()
        self.events = []

    def execute(self, command, **kwargs):
        if not self.conn.is_open():
            self.open()
        id = binascii.b2a_hex(os.urandom(4)).decode()
        cmd = {"execute": command, "id": id}
        if kwargs:
            cmd["arguments"] = kwargs
        self._write(cmd)
        response = None
        for message in self._read():
            if "id" in message and message["id"] == id:
                response = message
            elif "event" in message:
                self.events.append(message)
            elif "error" in message:
                response = message
        if not response:
            return None
        if "error" in response:
            raise RuntimeError(response["error"]["desc"])
        return response["return"]

    def _write(self, message):
        message = json.dumps(message) + "\n"
        logging.debug(f">>> {message}".strip())
        self.conn.write(message)

    def _read(self):
        response = b""
        while True:
            data = self.conn.read(1024)
            response += data
            if len(data) < 1024:
                break
        for message in response.decode().splitlines():
            logging.debug(f"<<< {message}".strip())
            yield json.loads(message)

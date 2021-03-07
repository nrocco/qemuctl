import binascii
import json
import logging
import os
import socket


class Qmp:
    """
    https://github.com/qemu/qemu/blob/master/docs/interop/qmp-spec.txt
    https://qemu.readthedocs.io/en/latest/interop/qemu-qmp-ref.html
    https://qemu.readthedocs.io/en/latest/system/monitor.html
    https://gist.github.com/rgl/dc38c6875a53469fdebb2e9c0a220c6c
    """
    def __init__(self, path):
        self.events = []
        self.path = path
        self.socket = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        self.events = []
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(self.path)
        if len(list(self._read())) == 0:
            raise RuntimeError("Qmp monitor not available")
        self.execute("qmp_capabilities", enable=["oob"])

    def close(self):
        if not self.socket:
            return
        self.socket.close()
        logging.debug(">>> EOF")
        self.socket = None
        self.events = []

    def execute(self, command, **kwargs):
        if not self.socket:
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
        os.write(self.socket.fileno(), message.encode())

    def _read(self):
        response = b""
        while True:
            data = os.read(self.socket.fileno(), 1024)
            response += data
            if len(data) < 1024:
                break
        for message in response.decode().splitlines():
            logging.debug(f"<<< {message}".strip())
            yield json.loads(message)

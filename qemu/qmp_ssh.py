import binascii
import json
import logging
import os


class QmpSSH:
    def __init__(self, channel):
        self.events = []
        self.channel = channel
        if len(list(self._read())) == 0:
            raise RuntimeError("Qmp monitor not available")
        self.execute("qmp_capabilities", enable=["oob"])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.channel.close()

    def close(self):
        if not self.socket:
            return
        self.socket.close()
        logging.debug(">>> EOF")
        self.socket = None
        self.events = []

    def execute(self, command, **kwargs):
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
        self.channel.send(message)

    def _read(self):
        response = b""
        while True:
            data = self.channel.recv(1024)
            response += data
            if len(data) < 1024:
                break
        for message in response.decode().splitlines():
            logging.debug(f"<<< {message}".strip())
            yield json.loads(message)

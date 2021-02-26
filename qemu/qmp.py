import binascii
import json
import logging
import os
import subprocess


class Qmp:
    """
    https://github.com/qemu/qemu/blob/master/docs/interop/qmp-spec.txt
    https://qemu.readthedocs.io/en/latest/interop/qemu-qmp-ref.html
    https://qemu.readthedocs.io/en/latest/system/monitor.html
    https://gist.github.com/rgl/dc38c6875a53469fdebb2e9c0a220c6c
    """
    def __init__(self, host, socket):
        self.command = ["ssh", host, "--", "socat", "-", "UNIX-CONNECT:{}".format(socket)]

    def __enter__(self):
        self.events = []
        self.proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if len(list(self._read())) == 0:
            raise RuntimeError("Qmp monitor not available")
        self.execute("qmp_capabilities", enable=["oob"])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.proc:
            return
        self.proc.terminate()
        self.proc = None
        self.events = None

    def execute(self, command, **kwargs):
        id = binascii.b2a_hex(os.urandom(4)).decode()
        cmd = {"execute": command, "id": id}
        if kwargs:
            cmd['arguments'] = kwargs
        self._write(cmd)
        response = None
        for message in self._read():
            if 'id' in message and message['id'] == id:
                response = message
            elif 'event' in message:
                self.events.append(message)
        if not response:
            return None
        if 'error' in response:
            raise RuntimeError(response['error']['desc'])
        return response['return']

    def _write(self, message):
        message = json.dumps(message) + "\n"
        logging.debug(f">>> {message}".strip())
        os.write(self.proc.stdin.fileno(), message.encode())

    def _read(self):
        response = b''
        while True:
            data = os.read(self.proc.stdout.fileno(), 1024)
            response += data
            if len(data) < 1024:
                break
        for message in response.decode().splitlines():
            logging.debug(f"<<< {message}".strip())
            yield json.loads(message)

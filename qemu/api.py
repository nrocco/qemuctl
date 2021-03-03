import json
import os
import shutil
import signal
import subprocess

from functools import wraps
from flask import Flask, request, jsonify

from .qmp import Qmp
from .specs import VmSpec


VNC_ADDRESS = "192.168.255.1"
VNC_PASSWORD = "xyfOhwJY"


app = Flask(__name__)


def get_dir(*parts):
    return os.path.abspath(os.path.normpath(os.path.join(*parts)))


def pass_vm(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        path = get_dir('vms', kwargs['name'])
        if not os.path.isdir(path):
            return jsonify(message=f"vm {kwargs['name']} not found"), 404
        with open(get_dir(path, 'spec.json'), 'r') as file:
            kwargs['spec'] = VmSpec(json.load(file))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/vms', methods=['GET'])
def vms_list():
    vms = []
    for name in os.listdir('vms'):
        with open(get_dir('vms', name, 'spec.json'), 'r') as file:
            vms.append({
                'name': name,
                'spec': VmSpec(json.load(file)),
            })
    return jsonify(vms)


@app.route('/vms', methods=['POST'])
def vms_post():
    data = request.get_json()
    chroot = get_dir('vms', data["name"])
    if os.path.isdir(chroot):
        return jsonify(message=f"vm {data['name']} already exists"), 400
    spec = VmSpec(data, {
        "chroot": chroot,
        "pidfile": f"{chroot}/pidfile",
        "qmp": f"unix:{chroot}/qmp.sock,server=yes,wait=no",
        "vnc": {
            "vnc": VNC_ADDRESS,
            "to": "100",
            "password": VNC_PASSWORD,
        },
        "writeconfig": f"{chroot}/config.cfg",
    })
    os.makedirs(spec['chroot'])
    with open(get_dir(spec["chroot"], "spec.json"), "w") as file:
        json.dump(spec, file)
    for drive in spec["drives"]:
        if os.path.isfile(drive["file"]):
            continue
        if "size" not in drive and "backing_file" not in drive:
            continue
        subprocess.run(drive.to_qemu_img_args(), text=True, capture_output=True, check=True)
    return vms_post_start(spec["name"])


@app.route('/vms/<name>', methods=['GET'])
@pass_vm
def vms_get(name, spec):
    try:
        with Qmp(get_dir(spec['chroot'], 'qmp.sock')) as qmp:
            status = qmp.execute("query-status")
            vnc = qmp.execute("query-vnc")
            vnc['url'] = f"vnc://:{spec['vnc']['password']}@{vnc['host']}:{vnc['service']}"
    except ConnectionRefusedError:
        status = {'status': 'stopped'}
        vnc = None
    return jsonify(name=name, status=status, vnc=vnc, spec=spec)


@app.route('/vms/<name>/start', methods=['POST'])
@pass_vm
def vms_post_start(name, spec):
    subprocess.run(spec.to_qemu_args(), text=True, capture_output=True, check=True)
    with Qmp(get_dir(spec['chroot'], 'qmp.sock')) as qmp:
        if spec["vnc"]["password"]:
            qmp.execute("change-vnc-password", password=spec["vnc"]["password"])
        qmp.execute("cont")
    return vms_get(name, spec)


@app.route('/vms/<name>/restart', methods=['POST'])
@pass_vm
def vms_post_restart(name, spec):
    with Qmp(get_dir(spec['chroot'], 'qmp.sock')) as qmp:
        qmp.execute("system_reset")
    return vms_get(name, spec)


@app.route('/vms/<name>/stop', methods=['POST'])
@pass_vm
def vms_post_stop(name, spec):
    with Qmp(get_dir(spec['chroot'], 'qmp.sock')) as qmp:
        qmp.execute("quit")
    return vms_get(name, spec)


@app.route('/vms/<name>', methods=['DELETE'])
@pass_vm
def vms_delete(name, spec):
    pidfile = get_dir(spec['chroot'], 'pidfile')
    if os.path.isfile(pidfile):
        with open(pidfile, 'r') as file:
            pid = int(file.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    shutil.rmtree(get_dir('vms', name))
    return jsonify(None), 204


@app.route('/vms/<name>/drives', methods=['GET'])
@pass_vm
def vms_get_drives(name, spec):
    drives = []
    for drive in spec['drives']:
        output = subprocess.run(["qemu-img", "info", "--backing-chain", "--output=json", drive['file']], text=True, capture_output=True, check=True)
        drives.append(json.loads(output.stdout))
    return jsonify(drives)

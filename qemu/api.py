import ipaddress
import json
import os
import shutil
import subprocess

from flask import Flask, request, jsonify
from functools import wraps

from .dnsmasq import get_dnsmasq_config
from .qmp import Qmp
from .specs import VmSpec


VNC_ADDRESS = "192.168.255.1"
VNC_PASSWORD = "xyfOhwJY"


app = Flask(__name__)


def run(command):
    return subprocess.run(command, text=True, capture_output=True, check=True)


def get_dir(*parts):
    return os.path.abspath(os.path.normpath(os.path.join(*parts)))


def pid_cmdline(pidfile):
    with open(pidfile, "r") as file:
        pid = file.read().strip()
    with open(f"/proc/{pid}/cmdline", "r") as file:
        cmdline = file.read().strip()
    return cmdline


def pid_kill(pidfile, name=None):
    args = ["pkill", "--pidfile", pidfile]
    if name:
        args += [name]
    return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def pid_exists(pidfile, name=None):
    args = ["pgrep", "--pidfile", pidfile]
    if name:
        args += [name]
    return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def pass_vm(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        path = get_dir("vms", kwargs["name"])
        if not os.path.isdir(path):
            return jsonify(message=f"vm {kwargs['name']} not found"), 404
        if "spec" not in kwargs:
            with open(get_dir(path, "spec.json"), "r") as file:
                kwargs["spec"] = VmSpec(json.load(file))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/", methods=["GET"])
def root():
    return jsonify([
        "/images",
        "/networks",
        "/vms",
    ])


@app.route("/vms", methods=["GET"])
def vms_list():
    vms = []
    for name in os.listdir("vms"):
        with open(get_dir("vms", name, "spec.json"), "r") as file:
            spec = VmSpec(json.load(file))
        vms.append({
            "name": name,
            "spec": spec,
            "status": "running" if pid_exists(spec["pidfile"], "qemu") else "stopped",
        })
    return jsonify(vms)


@app.route("/vms", methods=["POST"])
def vms_post():
    data = request.get_json()
    chroot = get_dir("vms", data["name"])
    if os.path.isdir(chroot):
        return jsonify(message=f"vm {data['name']} already exists"), 400
    spec = VmSpec(data, {
        "chroot": chroot,
        "pidfile": f"{chroot}/pidfile",
        "runas": "qemu",
        "qmp": f"unix:{chroot}/qmp.sock,server=yes,wait=no",
        "vnc": {
            "vnc": VNC_ADDRESS,
            "to": "100",
            "password": VNC_PASSWORD,
        },
        "writeconfig": f"{chroot}/config.cfg",
    })
    os.makedirs(spec["chroot"])
    with open(get_dir(spec["chroot"], "spec.json"), "w") as file:
        json.dump(spec, file)
    for drive in spec["drives"]:
        if os.path.isfile(drive["file"]):
            continue
        if "size" not in drive and "backing_file" not in drive:
            continue
        run(drive.to_qemu_img_args())
    return vms_post_start(name=spec["name"], spec=spec)


@app.route("/vms/<name>", methods=["GET"])
@pass_vm
def vms_get(name, spec):
    vnc = None
    if pid_exists(spec["pidfile"], "qemu"):
        with Qmp(get_dir(spec["chroot"], "qmp.sock")) as qmp:
            vnc_data = qmp.execute("query-vnc")
        vnc = f"vnc://:{spec['vnc']['password']}@{vnc_data['host']}:{vnc_data['service']}"
    state = False  # TODO pid_cmdline(spec["pidfile"]) == "\x00".join(spec.to_qemu_args())
    return jsonify(name=name, vnc=vnc, spec=spec, status="running" if vnc else "stopped", state="synced" if state else "dirty")


@app.route("/vms/<name>/start", methods=["POST"])
@pass_vm
def vms_post_start(name, spec):
    run(spec.to_qemu_args())
    with Qmp(get_dir(spec["chroot"], "qmp.sock")) as qmp:
        if spec["vnc"]["password"]:
            qmp.execute("change-vnc-password", password=spec["vnc"]["password"])
        qmp.execute("cont")
    return vms_get(name=name, spec=spec)


@app.route("/vms/<name>/restart", methods=["POST"])
@pass_vm
def vms_post_restart(name, spec):
    with Qmp(get_dir(spec["chroot"], "qmp.sock")) as qmp:
        qmp.execute("system_reset")
    return vms_get(name=name, spec=spec)


@app.route("/vms/<name>/stop", methods=["POST"])
@pass_vm
def vms_post_stop(name, spec):
    with Qmp(get_dir(spec["chroot"], "qmp.sock")) as qmp:
        qmp.execute("quit")
    return vms_get(name=name, spec=spec)


@app.route("/vms/<name>", methods=["DELETE"])
@pass_vm
def vms_delete(name, spec):
    pid_kill(spec["pidfile"], "qemu")
    shutil.rmtree(get_dir("vms", name))
    return jsonify(None), 204


@app.route("/vms/<name>/drives", methods=["GET"])
@pass_vm
def vms_get_drives(name, spec):
    drives = []
    for drive in spec["drives"]:
        output = run(["qemu-img", "info", "--output=json", drive["file"]])
        drives.append(json.loads(output.stdout))
    return jsonify(drives)


@app.route("/images", methods=["GET"])
def images_list():
    images = []
    for name in os.listdir("images"):
        output = run(["qemu-img", "info", "--output=json", get_dir("images", name)])
        images.append({
            "name": name,
            "spec": json.loads(output.stdout),
        })
    return jsonify(images)


@app.route("/images/<name>", methods=["GET"])
def images_get(name):
    file = get_dir("images", name)
    if not os.path.isfile(file):
        return jsonify(message=f"Image {name} does not exist"), 404
    output = run(["qemu-img", "info", "--output=json", file])
    return jsonify(json.loads(output.stdout))


@app.route("/images/<name>", methods=["DELETE"])
def images_delete(name):
    file = get_dir("images", name)
    if not os.path.isfile(file):
        return jsonify(message=f"Image {name} does not exist"), 404
    os.remove(file)
    return jsonify(None), 204

    def list_networks(self, details=False):
        return self.run(["ls", "-lh1" if details else "-h1", self.get_networks_dir()]).stdout.splitlines()


@app.route("/networks", methods=["GET"])
def networks_list():
    networks = []
    for name in os.listdir("networks"):
        networks.append({
            "name": name,
            "spec": None  # TODO introduce spec files for networks
        })
    return jsonify(networks)


@app.route("/networks", methods=["POST"])
def networks_post():
    data = request.get_json()
    chroot = get_dir("networks", data["name"])
    os.makedirs(chroot)
    run(["ip", "link", "add", data["name"], "type", "bridge", "stp_state", "1"])
    run(["ip", "link", "set", data["name"], "up"])
    if data["ip_range"]:
        ip_range = ipaddress.ip_network(data["ip_range"])
        run(["ip", "addr", "add", str(ip_range[1]), "dev", data["name"]])
        if data["dhcp"]:
            dnsmasq_conf = get_dnsmasq_config(data["name"], chroot, ip_range)
            dnsmasq_conf_file = get_dir(chroot, "dnsmasq.conf")
            with open(dnsmasq_conf_file, "w") as file:
                json.dump(dnsmasq_conf, file)
            run(["dnsmasq", f"--conf-file={dnsmasq_conf_file}"])


@app.route("/networks/<name>", methods=["GET"])
def networks_get(name):
    chroot = get_dir("networks", name)
    if not os.path.isdir(chroot):
        jsonify(f"Network {name} does not exist"), 404
    data = {}
    leases_file = get_dir(chroot, "leases")
    if os.path.isfile(leases_file):
        data["leases"] = []
        with open(leases_file, "r") as file:
            leases = file.readlines()
        for lease in leases:
            lease = lease.strip().split(" ")
            data["leases"].append({
                "timestamp": lease[0],
                "mac": lease[1],
                "ip": lease[2],
                "host": lease[3],
                "id": lease[4],
            })
    data["routes"] = json.loads(run(["ip", "-j", "route", "show", "dev", name]).stdout)
    data["arp"] = json.loads(run(["ip", "-j", "neigh", "show", "dev", name]).stdout)
    data["address"] = json.loads(run(["ip", "-j", "addr", "show", "dev", name]).stdout)
    data["link"] = json.loads(run(["ip", "-j", "link", "show", "master", name, "type", "bridge_slave"]).stdout)
    data["stats"] = json.loads(run(["ifstat", "-j", name]).stdout)
    return jsonify(data)


@app.route("/networks/<name>", methods=["DELETE"])
def networks_delete(name):
    pid_kill(get_dir("networks", name, "pidfile"), "dnsmasq")
    try:
        run(["ip", "link", "delete", name])
    except subprocess.CalledProcessError:
        pass
    shutil.rmtree(get_dir("networks", name))
    return jsonify(None), 204

from flask import Flask, request, jsonify
from functools import wraps

from .hypervisor import Hypervisor
from .specs import NetworkSpec
from .specs import VmSpec


app = Flask(__name__)

hypervisor = Hypervisor("")


def pass_vm(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            kwargs['vm'] = hypervisor.vms.get(kwargs["name"])
        except Exception as e:
            return jsonify(message=str(e)), 404
        return f(*args, **kwargs)
    return decorated_function


def pass_image(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            kwargs['image'] = hypervisor.images.get(kwargs["name"])
        except Exception as e:
            return jsonify(message=str(e)), 404
        return f(*args, **kwargs)
    return decorated_function


def pass_network(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            kwargs['network'] = hypervisor.networks.get(kwargs["name"])
        except Exception as e:
            return jsonify(message=str(e)), 404
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
    brief = request.args.get("brief", "").lower() in ["true", "yes", "y", "1"]
    vms = []
    for vm in hypervisor.vms.all():
        vms.append({
            "name": vm.name,
            "spec": None if brief else vm.spec,
            "status": "running" if vm.is_running else "stopped",
        })
    return jsonify(vms), 200


@app.route("/vms", methods=["POST"])
def vms_post():
    spec = VmSpec(request.get_json())
    vm = hypervisor.vms.create(spec).start()
    return vms_get(name=vm.name, vm=vm)


@app.route("/vms/<string:name>", methods=["GET"])
@pass_vm
def vms_get(name, vm):
    vnc = None
    spec = vm.spec
    if vm.is_running:
        with vm.monitor as monitor:
            vnc_data = monitor.execute("query-vnc")
        vnc = f"vnc://:{spec['vnc']['password']}@{vnc_data['host']}:{vnc_data['service']}"
    if spec["nics"]:
        ips = [lease for lease in vm.hypervisor.networks.get(spec["nics"][0]["br"]).leases if lease["mac"] == spec["nics"][0]["mac"]]
    state = False
    return jsonify(name=name, vnc=vnc, spec=spec, ips=ips, status="running" if vnc else "stopped", state="synced" if state else "dirty"), 200


@app.route("/vms/<string:name>/start", methods=["POST"])
@pass_vm
def vms_post_start(name, vm):
    vm.start()
    return vms_get(name=name, vm=vm)


@app.route("/vms/<string:name>/restart", methods=["POST"])
@pass_vm
def vms_post_restart(name, vm):
    vm.restart()
    return vms_get(name=name, vm=vm)


@app.route("/vms/<string:name>/stop", methods=["POST"])
@pass_vm
def vms_post_stop(name, vm):
    vm.stop()
    return '', 204


@app.route("/vms/<string:name>/monitor", methods=["POST"])
@pass_vm
def vms_post_monitor(name, vm):
    data = request.get_json()
    with vm.monitor as monitor:
        result = monitor.execute(data["command"], **data["arguments"])
    return jsonify(result), 200


@app.route("/vms/<string:name>", methods=["DELETE"])
@pass_vm
def vms_delete(name, vm):
    vm.destroy()
    return '', 204


@app.route("/vms/<string:name>/drives", methods=["GET"])
@pass_vm
def vms_get_drives(name, vm):
    return jsonify(vm.drives), 200


@app.route("/images", methods=["GET"])
def images_list():
    brief = request.args.get("brief", "").lower() in ["true", "yes", "y", "1"]
    images = []
    for image in hypervisor.images.all():
        images.append({
            "name": image.name,
            "spec": None if brief else image.spec,
        })
    return jsonify(images), 200


@app.route("/images/<path:name>", methods=["GET"])
@pass_image
def images_get(name, image):
    return jsonify(image.spec), 200


@app.route("/images/<path:name>", methods=["DELETE"])
@pass_image
def images_delete(name, image):
    image.delete()
    return '', 204


@app.route("/networks", methods=["GET"])
def networks_list():
    brief = request.args.get("brief", "").lower() in ["true", "yes", "y", "1"]
    networks = []
    for network in hypervisor.networks.all():
        networks.append({
            "name": network.name,
            "spec": None if brief else network.spec,
        })
    return jsonify(networks), 200


@app.route("/networks", methods=["POST"])
def networks_post():
    spec = NetworkSpec(request.get_json())
    hypervisor.networks.create(spec).start()
    return '', 204


@app.route("/networks/<string:name>", methods=["GET"])
@pass_network
def networks_get(name, network):
    return jsonify({
        "spec": network.spec,
        "leases": network.leases,
        "routes": network.routes,
        "arp": network.arp,
        "address": network.address,
        "link": network.link,
        "stats": network.stats,
    }), 200


@app.route("/networks/<string:name>", methods=["DELETE"])
@pass_network
def networks_delete(name, network):
    network.destroy()
    return '', 204

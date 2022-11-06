import json
import os
import shutil
import subprocess

from .specs import NetworkSpec


class Network:
    @staticmethod
    def create_from_spec(hypervisor, spec):
        network = Network(hypervisor, spec["name"])
        network.hypervisor.make_dir(network.directory)
        with network.hypervisor.open_file(os.path.join(network.directory, "spec.json"), "w") as file:
            json.dump(spec, file)
        if spec["ip_range"] and spec["dhcp"]:
            with network.hypervisor.open_file(os.path.join(network.directory, "dnsmasq.conf"), "w") as file:
                file.write(generate_dnsmasq_config(spec))
        return network

    def __init__(self, hypervisor, name):
        self.hypervisor = hypervisor
        self.name = name
        self.directory = os.path.join(self.hypervisor.networks.directory, self.name)

    def __repr__(self):
        return f"<Network {self.name}>"

    @property
    def spec(self):
        with self.hypervisor.open_file(os.path.join(self.directory, "spec.json"), "r") as file:
            data = json.load(file)
        return NetworkSpec(data)

    @property
    def bridge(self):
        return json.loads(self.hypervisor.exec(["ip", "-j", "link", "show", "dev", self.name]).stdout)[0]

    @property
    def routes(self):
        return json.loads(self.hypervisor.exec(["ip", "-j", "route", "show", "dev", self.name]).stdout)

    @property
    def arp(self):
        return json.loads(self.hypervisor.exec(["ip", "-j", "neigh", "show", "dev", self.name]).stdout)

    @property
    def address(self):
        return json.loads(self.hypervisor.exec(["ip", "-j", "addr", "show", "dev", self.name]).stdout)

    @property
    def link(self):
        return json.loads(self.hypervisor.exec(["ip", "-j", "link", "show", "master", self.name, "type", "bridge_slave"]).stdout)

    @property
    def stats(self):
        return json.loads(self.hypervisor.exec(["ifstat", "-j", self.name]).stdout)

    @property
    def leases(self):
        leases_file = os.path.join(self.directory, "leases")
        if not self.hypervisor.is_file(leases_file):
            return []
        with self.hypervisor.open_file(leases_file, "r") as file:
            raw_leases = file.readlines()
        leases = []
        for lease in raw_leases:
            lease = lease.strip().split(" ")
            leases.append({
                "timestamp": lease[0],
                "mac": lease[1],
                "ip": lease[2],
                "host": lease[3],
                "id": lease[4],
            })
        return leases

    def start(self):
        try:
            bridge_address = self.address
        except subprocess.CalledProcessError:
            bridge_address = None
        spec = self.spec
        if not bridge_address:
            self.hypervisor.exec(["ip", "link", "add", spec["name"], "type", "bridge", "stp_state", "1"])
            self.hypervisor.exec(["ip", "link", "set", spec["name"], "up"])
        elif 'UP' not in bridge_address[0]['flags']:
            self.hypervisor.exec(["ip", "link", "set", spec["name"], "up"])
        if spec["ip_range"]:
            # TODO check if the ip already exists on the bridge
            self.hypervisor.exec(["ip", "addr", "add", f"{spec.ip_range[1]}/{spec.ip_range.prefixlen}", "dev", spec["name"]])
        if spec["dhcp"]:
            # TODO check if dnsmasq is already running
            self.hypervisor.exec(["dnsmasq", "--conf-file=dnsmasq.conf"], cwd=self.directory)
        return self

    def stop(self):
        if self.spec['dhcp']:
            self.hypervisor.pid_kill(os.path.join(self.directory, "pidfile"), "dnsmasq")
        return self

    def destroy(self):
        self.stop()
        try:
            self.hypervisor.exec(["ip", "link", "delete", self.name])
        except subprocess.CalledProcessError:
            pass
        shutil.rmtree(self.directory)


class Networks:
    def __init__(self, hypervisor):
        self.hypervisor = hypervisor
        self.directory = os.path.join(hypervisor.directory, "networks")

    def __contains__(self, value):
        return self.hypervisor.is_dir(os.path.join(self.directory, value))

    def all(self):
        if not self.hypervisor.is_dir(self.directory):
            return []
        return [Network(self.hypervisor, name) for name in self.hypervisor.list_dir(self.directory)]

    def get(self, name):
        if name not in self:
            raise Exception(f"Network {name} does not exist")
        return Network(self.hypervisor, name)

    def create(self, spec):
        if spec["name"] in self:
            raise Exception("Network already exists")
        return Network.create_from_spec(self.hypervisor, spec)


def generate_dnsmasq_config(spec):
    config = [
        "pid-file=pidfile",
        f"interface={spec['name']}",
        "except-interface=lo",
        "bind-interfaces",
        "no-poll",
        "user=qemu",
    ]
    if spec['logging']:
        config += [
            "log-dhcp",
            "log-queries",
            "log-facility=./dnsmasq.log",
        ]
    if spec['dns']:
        config += [
            "strict-order",
            "domain-needed",
            "bogus-priv",
            "no-hosts",
            "addn-hosts=addnhosts",
        ]
    else:
        config += [
            "port=0",
        ]
    if spec.ip_range:
        config += [
            f"dhcp-range={spec.ip_range[2]},{spec.ip_range[-2]},{spec.ip_range.netmask}",
            "dhcp-no-override",
            "dhcp-authoritative",
            f"dhcp-option=6,{spec['nameserver']}",
            f"dhcp-lease-max={spec.ip_range.num_addresses - 3}",
            "dhcp-hostsfile=hostsfile",
            "dhcp-leasefile=leases",
        ]
    return "\n".join(config)

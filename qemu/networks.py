import json
import os

from .specs import NetworkSpec


class Network:
    @staticmethod
    def create_from_spec(hypervisor, spec):
        network = Network(hypervisor, spec["name"])
        network.hypervisor.make_dir(network.directory)
        with network.hypervisor.open_file(os.path.join(network.directory, "spec.json"), "w") as file:
            json.dump(spec, file)
        if spec["dhcp"] or spec['tftp'] or spec['dns']:
            with network.hypervisor.open_file(os.path.join(network.directory, "dnsmasq.conf"), "w") as file:
                file.write(generate_dnsmasq_config(spec, network.directory))
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
    def is_running(self):
        pidfile = os.path.join(self.directory, "pidfile")
        if not self.hypervisor.is_file(pidfile):
            return False
        return self.hypervisor.pid_exists(pidfile, "dnsmasq")

    @property
    def bridge(self):
        return json.loads(self.hypervisor.exec(["ip", "-json", "-details", "-statistics", "link", "show", "dev", self.name]))[0]

    @property
    def routes(self):
        return json.loads(self.hypervisor.exec(["ip", "-json", "-details", "-statistics", "route", "show", "dev", self.name]))

    @property
    def arp(self):
        return json.loads(self.hypervisor.exec(["ip", "-json", "-details", "-statistics", "neigh", "show", "dev", self.name]))

    @property
    def address(self):
        return json.loads(self.hypervisor.exec(["ip", "-json", "-details", "-statistics", "addr", "show", "dev", self.name], check=False) or "[]")

    @property
    def link(self):
        return json.loads(self.hypervisor.exec(["ip", "-json", "-details", "-statistics", "link", "show", "master", self.name, "type", "bridge_slave"]))

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
        bridge_address = self.address
        spec = self.spec
        if not bridge_address:
            self.hypervisor.exec(["ip", "link", "add", spec["name"], "type", "bridge", "stp_state", "1", "forward_delay", "2"])
            self.hypervisor.exec(["ip", "link", "set", spec["name"], "up"])
        elif 'UP' not in bridge_address[0]['flags']:
            self.hypervisor.exec(["ip", "link", "set", spec["name"], "up"])
        if spec["ip_range"]:
            if 0 == len([addr for addr in self.address[0]['addr_info'] if addr['local'] == str(spec.ip_range[1])]):
                self.hypervisor.exec(["ip", "addr", "add", f"{spec.ip_range[1]}/{spec.ip_range.prefixlen}", "dev", spec["name"]])
            self.hypervisor.exec(["iptables", "-t", "nat", "-A", "POSTROUTING", "-s", f"{spec.ip_range[0]}/{spec.ip_range.prefixlen}", "-j", "MASQUERADE"])
        if spec["dhcp"] or spec['tftp'] or spec['dns']:
            if not self.hypervisor.pid_exists(os.path.join(self.directory, "pidfile"), "dnsmasq"):
                self.hypervisor.exec(["dnsmasq", f"--conf-file={self.directory}/dnsmasq.conf"], cwd=self.directory)
        self.hypervisor.exec(["sysctl", "net.ipv4.ip_forward=1"])
        return self

    def stop(self):
        spec = self.spec
        if spec['dhcp']:
            self.hypervisor.pid_kill(os.path.join(self.directory, "pidfile"), "dnsmasq")
        if spec["ip_range"]:
            self.hypervisor.exec(["iptables", "-t", "nat", "-D", "POSTROUTING", "-s", f"{spec.ip_range[0]}/{spec.ip_range.prefixlen}", "-j", "MASQUERADE"])
        return self

    def destroy(self):
        self.stop()
        self.hypervisor.exec(["ip", "link", "delete", self.name], check=False)
        self.hypervisor.remove_dir(self.directory)


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


def generate_dnsmasq_config(spec, directory):
    config = [
        f"pid-file={directory}/pidfile",
        f"interface={spec['name']}",
        "except-interface=lo",
        "bind-interfaces",
        "no-poll",
        "user=nobody",
        f"log-facility={directory}/dnsmasq.log",
    ]
    if spec['dhcp']:
        config += [
            "log-dhcp",
            f"dhcp-range={spec.ip_range[2]},{spec.ip_range[-2]},{spec.ip_range.netmask}",
            "dhcp-no-override",
            "dhcp-authoritative",
            "dhcp-ignore-names",
            "no-ping",
            f"dhcp-option=6,{spec.ip_range[1] if spec['dns'] else '1.1.1.1'}",
            f"dhcp-lease-max={spec.ip_range.num_addresses - 3}",
            f"dhcp-hostsfile={directory}/hostsfile",
            f"dhcp-leasefile={directory}/leases",
        ]
    if spec['tftp']:
        config += [
            "enable-tftp",
            f"tftp-root={directory}/tftp",
            # "dhcp-match=set:efi-x86_64,option:client-arch,7",
            # "dhcp-match=set:efi-x86_64,option:client-arch,9",
            # "dhcp-match=set:efi-aarch64,option:client-arch,11",
            # "dhcp-match=set:bios,option:client-arch,0",
            # "dhcp-boot=tag:efi-x86_64,ipxe.efi",
            # "dhcp-boot=tag:bios,undionly.kpxe",
            # "dhcp-boot=tag:efi-aarch64,snponly.efi",
        ]
    if spec['dns']:
        config += [
            "domain-needed",
            "bogus-priv",
            "no-hosts",
            "log-queries",
            "local-service",
            "dhcp-fqdn" if spec['dhcp'] else "",
            "domain=qemuctl.local",  # TODO make this configurable
            "addn-hosts=addnhosts",
        ]
    else:
        config += [
            "port=0",
        ]
    return "\n".join(config) + "\n"

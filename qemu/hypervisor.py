import json
import subprocess

from .dnsmasq import get_dnsmasq_config


class Hypervisor:
    def list_images(self, details=False):
        return self.run(["ls", "-lh1" if details else "-h1", self.get_images_dir()]).stdout.splitlines()

    def list_networks(self, details=False):
        return self.run(["ls", "-lh1" if details else "-h1", self.get_networks_dir()]).stdout.splitlines()

    def get_image(self, image):
        result = self.run(["qemu-img", "info", "--backing-chain", "--output=json", self.get_images_dir(image)])
        return json.loads(result.stdout)

    def delete_image(self, image):
        self.run(["rm", self.get_images_dir(image)])

    def get_leases(self, network):
        leases = []
        result = self.run(["cat", self.get_networks_dir(network, "leases")])
        for line in result.stdout.splitlines():
            data = line.split(" ")
            leases.append({
                "timestamp": data[0],
                "mac": data[1],
                "ip": data[2],
                "host": data[3],
                "id": data[4],
            })
        return leases

    def create_network(self, name, dhcp=False, ip_range=None):
        self.run(["mkdir", self.get_networks_dir(name)])
        self.run(["ip", "link", "add", name, "type", "bridge", "stp_state", "1"])
        self.run(["ip", "link", "set", name, "up"])
        if ip_range:
            self.run(["ip", "addr", "add", str(ip_range[1]), "dev", name])
        if dhcp:
            dnsmasq_conf = get_dnsmasq_config(name, self.get_networks_dir(name), ip_range)
            self.run(["tee", self.get_networks_dir(name, "dnsmasq.conf")], input=dnsmasq_conf)
            conf_file = self.get_networks_dir(name, "dnsmasq.conf")
            self.run(["dnsmasq", f"--conf-file={conf_file}"])

    def destroy_network(self, name):
        try:
            self.run(["pkill", "--pidfile", self.get_networks_dir(name, 'pidfile'), "dnsmasq"])
        except subprocess.CalledProcessError:
            pass
        try:
            self.run(["ip", "link", "delete", name])
        except subprocess.CalledProcessError:
            pass
        self.run(["rm", "-rf", self.get_networks_dir(name)])

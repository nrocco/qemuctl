import os


def get_dnsmasq_config(spec):
    config = [
        f"pid-file={spec['chroot']}/pidfile",
        f"interface={spec['name']}",
        "except-interface=lo",
        "bind-interfaces",
        "user=qemu",
    ]
    if spec['logging']:
        config += [
            "log-queries",
            f"log-facility={spec['chroot']}/dnsmasq.log",
        ]
    if spec['dns']:
        config += [
            "strict-order",
            "domain-needed",
            "bogus-priv",
            "no-hosts",
            f"addn-hosts={spec['chroot']}/addnhosts",
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
            f"dhcp-hostsfile={spec['chroot']}/hostsfile",
            f"dhcp-leasefile={spec['chroot']}/leases",
        ]
    return "\n".join(config)


def get_dnsmasq_leases(leases_file, mac=None, ip=None):
    if not os.path.isfile(leases_file):
        return []
    with open(leases_file, "r") as file:
        raw_leases = file.readlines()
    leases = []
    for lease in raw_leases:
        lease = lease.strip().split(" ")
        if mac and mac != lease[1]:
            continue
        if ip and ip != lease[2]:
            continue
        leases.append({
            "timestamp": lease[0],
            "mac": lease[1],
            "ip": lease[2],
            "host": lease[3],
            "id": lease[4],
        })
    return leases

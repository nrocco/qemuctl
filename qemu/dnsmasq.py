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

def get_dnsmasq_config(interface, directory, ip_range=None, logging=True, dns=False):
    config = [
        f"pid-file={directory}/pidfile",
        f"interface={interface}",
        "except-interface=lo",
        "bind-interfaces",
    ]
    if logging:
        config += [
            "log-queries",
            f"log-facility={directory}/dnsmasq.log",
        ]
    if dns:
        config += [
            "strict-order",
            "domain-needed",
            "bogus-priv",
            "no-hosts",
            f"addn-hosts={directory}/addnhosts",
        ]
    else:
        config += [
            "port=0",
        ]
    if ip_range:
        config += [
            f"dhcp-range={ip_range[2]},{ip_range[-2]},{ip_range.netmask}",
            "dhcp-no-override",
            "dhcp-authoritative",
            f"dhcp-lease-max={ip_range.num_addresses - 3}",
            f"dhcp-hostsfile={directory}/hostsfile",
            f"dhcp-leasefile={directory}/leases",
        ]
    return '\n'.join(config)

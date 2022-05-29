from qemu.networks import generate_dnsmasq_config
from qemu.specs import NetworkSpec


def test_config_with_basics():
    spec = NetworkSpec({"name": "br0", "logging": False})
    config = generate_dnsmasq_config(spec)
    assert "pid-file=pidfile" in config
    assert "interface=br0" in config
    assert "except-interface=lo" in config
    assert "bind-interfaces" in config
    assert "port=0" in config
    assert "log-queries" not in config


def test_config_with_logging():
    spec = NetworkSpec({"name": "br0"})
    config = generate_dnsmasq_config(spec)
    assert "log-queries" in config
    assert "log-facility=dnsmasq.log" in config


def test_config_with_dns():
    spec = NetworkSpec({"name": "br0", "dns": True})
    config = generate_dnsmasq_config(spec)
    assert "strict-order" in config
    assert "domain-needed" in config
    assert "bogus-priv" in config
    assert "no-hosts" in config
    assert "addn-hosts=addnhosts" in config


def test_config_with_dhcp():
    spec = NetworkSpec({"name": "br0", "ip_range": "127.0.0.0/24"})
    config = generate_dnsmasq_config(spec)
    assert "dhcp-range=127.0.0.2,127.0.0.254,255.255.255.0" in config
    assert "dhcp-no-override" in config
    assert "dhcp-authoritative" in config
    assert "dhcp-lease-max=253" in config
    assert "dhcp-hostsfile=hostsfile" in config
    assert "dhcp-leasefile=leases" in config

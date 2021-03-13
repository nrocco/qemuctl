from qemu.dnsmasq import get_dnsmasq_config
from qemu.specs import NetworkSpec


def test_config_with_basics():
    config = get_dnsmasq_config(NetworkSpec({"name": "br0", "chroot": "/chroot", "logging": False}))
    assert "pid-file=/chroot/pidfile" in config
    assert "interface=br0" in config
    assert "except-interface=lo" in config
    assert "bind-interfaces" in config
    assert "port=0" in config
    assert "log-queries" not in config


def test_config_with_logging():
    config = get_dnsmasq_config(NetworkSpec({"name": "br0", "chroot": "/chroot"}))
    assert "log-queries" in config
    assert "log-facility=/chroot/dnsmasq.log" in config


def test_config_with_dns():
    config = get_dnsmasq_config(NetworkSpec({"name": "br0", "chroot": "/chroot", "dns": True}))
    assert "strict-order" in config
    assert "domain-needed" in config
    assert "bogus-priv" in config
    assert "no-hosts" in config
    assert "addn-hosts=/chroot/addnhosts" in config


def test_config_with_dhcp():
    config = get_dnsmasq_config(NetworkSpec({"name": "br0", "chroot": "/chroot", "ip_range": "127.0.0.0/24"}))
    assert "dhcp-range=127.0.0.2,127.0.0.254,255.255.255.0" in config
    assert "dhcp-no-override" in config
    assert "dhcp-authoritative" in config
    assert "dhcp-lease-max=253" in config
    assert "dhcp-hostsfile=/chroot/hostsfile" in config
    assert "dhcp-leasefile=/chroot/leases" in config

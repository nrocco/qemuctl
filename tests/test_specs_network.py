from qemu.specs import NetworkSpec


def test_network_spec():
    network = NetworkSpec(ip_range="127.0.0.0/24")
    assert network["ip_range"] == "127.0.0.0/24"


def test_network_spec_from_dict():
    network = NetworkSpec({
        "logging": False,
    })
    assert not network["ip_range"]
    assert not network["logging"]

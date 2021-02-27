import click
import json

from .utils import pass_hypervisor


@click.group()
def networks():
    """
    Manage networks
    """
    pass


@networks.command("list")
@pass_hypervisor
def networks_list(hypervisor):
    """
    List all available networks
    """
    pass  # TODO implement this


@networks.command("leases")
@click.argument("network")
@pass_hypervisor
def networks_leases(hypervisor, network):
    """
    List leases for a network
    """
    print(json.dumps(hypervisor.get_leases(network), indent=2))


@networks.command("create")
@click.argument("network")
@pass_hypervisor
def networks_create(hypervisor, network):
    """
    Start a network

    strict-order
    pid-file=/var/lib/qemu/networks/br0/br0.pid
    except-interface=lo
    bind-dynamic
    interface=br0
    dhcp-range=192.168.122.2,192.168.122.254,255.255.255.0
    dhcp-no-override
    dhcp-authoritative
    dhcp-lease-max=253
    dhcp-hostsfile=/var/lib/qemu/networks/br0/br0.hostsfile
    addn-hosts=/var/lib/qemu/networks/br0/br0.addnhosts
    dhcp-leasefile=/var/lib/qemu/networks/br0/br0.leases
    """
    print(f"Network {network} created")  # TODO implement this


@networks.command("start")
@click.argument("network")
@pass_hypervisor
def networks_start(hypervisor, network):
    """
    Start a network
    """
    hypervisor.start_network(network)
    print(f"Network {network} started")

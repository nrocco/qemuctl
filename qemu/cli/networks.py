import click
import json

from .utils import pass_hypervisor


@click.group()
def networks():
    """
    Manage networks.
    """
    pass


@networks.command()
@click.option("--details", is_flag=True, help="Show more details")
@pass_hypervisor
def ls(hypervisor, details):
    """
    List all available networks.
    """
    for network in hypervisor.list_networks(details):
        print(network)


@networks.command()
@click.option("--dhcp", is_flag=True, help="Enable dhcp server on this network")
@click.option("--address", help="Assign an ip address to this network")
@click.argument("network")
@pass_hypervisor
def create(hypervisor, network, dhcp, address):
    """
    Create a network.
    """
    # strict-order
    # pid-file=/var/lib/qemu/networks/br0/br0.pid
    # except-interface=lo
    # bind-dynamic
    # interface=br0
    # dhcp-range=192.168.122.2,192.168.122.254,255.255.255.0
    # dhcp-no-override
    # dhcp-authoritative
    # dhcp-lease-max=253
    # dhcp-hostsfile=/var/lib/qemu/networks/br0/br0.hostsfile
    # addn-hosts=/var/lib/qemu/networks/br0/br0.addnhosts
    # dhcp-leasefile=/var/lib/qemu/networks/br0/br0.leases
    hypervisor.create_network(network, dhcp, address)
    print(f"Network {network} created")


@networks.command()
@click.argument("network")
@pass_hypervisor
def destroy(hypervisor, network):
    """
    Destroy a network.
    """
    hypervisor.destroy_network(network)
    print(f"Network {network} destroy")


@networks.command()
@click.argument("network")
@pass_hypervisor
def leases(hypervisor, network):
    """
    List leases for a network.
    """
    print(json.dumps(hypervisor.get_leases(network), indent=2))

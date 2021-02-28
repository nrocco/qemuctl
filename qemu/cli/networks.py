import click
import json
import ipaddress

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
    for name in hypervisor.list_networks(details):
        print(name)


@networks.command()
@click.option("--ip-range", help="Assign an ip address to this network")
@click.option("--dhcp/--no-dhcp", default=True, help="Enable dhcp server on this network")
@click.argument("name")
@pass_hypervisor
def create(hypervisor, name, dhcp, ip_range):
    """
    Create a network.
    """
    if ip_range:
        ip_range = ipaddress.ip_network(ip_range)
    hypervisor.create_network(name, dhcp, ip_range)
    print(f"Network {name} created")


@networks.command()
@click.argument("name")
@pass_hypervisor
def destroy(hypervisor, name):
    """
    Destroy a network.
    """
    hypervisor.destroy_network(name)
    print(f"Network {name} destroy")


@networks.command()
@click.argument("name")
@pass_hypervisor
def leases(hypervisor, name):
    """
    List leases for a network.
    """
    print(json.dumps(hypervisor.get_leases(name), indent=2))

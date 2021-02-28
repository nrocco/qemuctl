import click

from .utils import pass_hypervisor


@click.group()
def system():
    """
    Manage the hypervisor itself.
    """
    pass


@system.command()
@pass_hypervisor
def show(hypervisor):
    """
    View all objects on this hypervisor.
    """
    print(hypervisor.run(["tree", hypervisor.state_directory]).stdout)

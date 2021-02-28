import click
import json

from .utils import pass_hypervisor


@click.group()
def images():
    """
    Manage images.
    """
    pass


@images.command()
@click.option("--details", is_flag=True, help="Show more details")
@pass_hypervisor
def ls(hypervisor, details):
    """
    List all available images.
    """
    for name in hypervisor.list_images(details):
        print(name)


@images.command()
@click.argument("name")
@pass_hypervisor
def show(hypervisor, name):
    """
    Show information about an image.
    """
    print(json.dumps(hypervisor.get_image(name), indent=2))


@images.command()
@click.argument("name")
@pass_hypervisor
def delete(hypervisor, name):
    """
    Delete an image.
    """
    hypervisor.delete_image(name)
    print(f"Image {name} deleted")

import click
import json

from .utils import pass_hypervisor


@click.group()
def images():
    """
    Manage images
    """
    pass


@images.command("list")
@click.option("--details", is_flag=True, help="Show more details")
@pass_hypervisor
def list_(hypervisor, details):
    """
    List all available images
    """
    for image in hypervisor.list_images(details):
        print(image)


@images.command("info")
@click.argument("image")
@pass_hypervisor
def info(hypervisor, image):
    """
    Get information about an image
    """
    print(json.dumps(hypervisor.get_image(image), indent=2))


@images.command("delete")
@click.argument("image")
@pass_hypervisor
def delete(hypervisor, image):
    """
    Remove an image
    """
    hypervisor.remove_image(image)
    print(f"Image {image} removed")

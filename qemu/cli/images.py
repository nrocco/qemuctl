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
@pass_hypervisor
def images_list(hypervisor):
    """
    List all available images
    """
    print("\n".join(hypervisor.list_images()))


@images.command("info")
@click.argument("image", nargs=1)
@pass_hypervisor
def images_info(hypervisor, image):
    """
    Get information about an image
    """
    print(json.dumps(hypervisor.get_image(image), indent=2))


@images.command("delete")
@click.argument("image", nargs=1)
@pass_hypervisor
def images_delete(hypervisor, image):
    """
    Remove an image
    """
    hypervisor.remove_image(image)
    print(f"Image {image} removed")

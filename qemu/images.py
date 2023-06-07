import json
import os


class Image:
    def __init__(self, hypervisor, name):
        self.hypervisor = hypervisor
        self.name = name
        self.file = os.path.join(self.hypervisor.images.directory, self.name)

    def __repr__(self):
        return f"<Image {self.name}>"

    @property
    def spec(self):
        return json.loads(self.hypervisor.exec(["qemu-img", "info", "--force-share", "--output=json", self.file]))

    def delete(self):
        self.hypervisor.remove_file(self.file)


class Images:
    def __init__(self, hypervisor):
        self.hypervisor = hypervisor
        self.directory = os.path.join(hypervisor.directory, "images")

    def all(self):
        if not self.hypervisor.is_dir(self.directory):
            return []
        images = []
        for file in self.hypervisor.walk(self.directory):
            name = os.path.relpath(file, start=self.directory)
            images.append(Image(self.hypervisor, name))
        return images

    def get(self, name):
        if not self.hypervisor.is_file(os.path.join(self.directory, name)):
            raise Exception(f"Image {name} does not exist")
        return Image(self.hypervisor, name)

    def create(self, spec):  # TODO: add download functionality here
        """
        get json https://app.vagrantup.com/generic/boxes/rocky9
        find most recent version number
        check if we have the version already
        wget --output-document=- https://app.vagrantup.com/generic/boxes/alpine317/versions/4.2.16/providers/libvirt.box | tar --extract --file=- box.img
        tar --extract --file libvirt.box --transform 's#box.img#fuu.img#' box.img
        """
        pass

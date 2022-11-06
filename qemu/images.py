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
        return json.loads(self.hypervisor.exec(["qemu-img", "info", "--force-share", "--output=json", self.file]).stdout)

    def delete(self):
        os.remove(self.file)


class Images:
    def __init__(self, hypervisor):
        self.hypervisor = hypervisor
        self.directory = os.path.join(hypervisor.directory, "images")

    def all(self):
        if not os.path.isdir(self.directory):
            return []
        images = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                name = os.path.relpath(os.path.join(root, file), start=self.directory)
                images.append(Image(self.hypervisor, name))
        return images

    def get(self, name):
        if not os.path.isfile(os.path.join(self.directory, name)):
            raise Exception(f"Image {name} does not exist")
        return Image(self.hypervisor, name)

    def create(self, spec):  # TODO: add download functionality here
        """
        get json https://app.vagrantup.com/generic/boxes/rocky9
        find most recent version number
        check if we have the version already
        wget -O- https://app.vagrantup.com/generic/boxes/rocky9/versions/4.1.20/providers/libvirt.box | tar xf - box.img
        """
        pass

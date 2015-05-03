# qemufile
a python based command line tool to manage qemu images


## usage

Use `pyqemu -h` to get help:

    usage: pyqemu [-h] [-c CONFIG_FILE] [-v] [-q] [-V]
                  {list,start,generate-mac} ...

    positional arguments:
      {list,start,generate-mac}
        list                list qemu boxes
        start               start a qemu box
        generate-mac        generate a mac address

    optional arguments:
      -h, --help            show this help message and exit
      -c CONFIG_FILE, --config CONFIG_FILE
                            path to the config file
      -v, --verbose         output more verbose
      -q, --quiet           surpress all output
      -V, --version         show program's version number and exit

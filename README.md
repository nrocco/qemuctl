qemuctl
=======

a python based command line tool to manage a plain qemu hypervisor


usage
-----

Use `qemuctl --help` to get help:

    Usage: qemuctl [OPTIONS] COMMAND [ARGS]...

      Manage virtual machines using qemu

    Options:
      --config TEXT           Location to a config file  [default: .qemuctl.json, ~/.config/qemuctl/config.json, /etc/qemuctl.json]
      --hypervisor TEXT       Hypervisor endpoint
      --state-directory TEXT  Directory on the hypervisor where all state is stored
      --vnc-address TEXT      Address for VNC monitors  [default: 127.0.0.1]
      --vnc-password TEXT     Default VNC password
      -v, --verbose           Verbose logging, repeat to increase verbosity
      --version               Show the version and exit.
      --help                  Show this message and exit.

    Commands:
      images    Manage images
      networks  Manage networks
      vms       Manage virtual machines

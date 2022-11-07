qemuctl
=======

a python based command line tool to manage a plain qemu hypervisor


dependencies
------------

- qemu
- iproute
- dnsmasq
- socat


setup
-----

Make sure we can attach `qemu` instances to all bridges (sometimes this is in `/etc/qemu-kvm/bridge.conf`):

    $ cat /etc/qemu/bridge.conf
    allow all


Enable ip forwarding in the kernel:

    sysctl -w net.ipv4.ip_forward=1


NAT traffic from the qemu bridge:

    iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE


usage
-----

Use `qemuctl --help` to get help:

    Usage: qemuctl [OPTIONS] COMMAND [ARGS]...

      Manage virtual machines using qemu.

    Options:
      --config TEXT       Location to a config file
      --hypervisor TEXT   Hypervisor endpoint
      --vnc-command TEXT  The vnc program to execute
      -v, --verbose       Verbose logging, repeat to increase verbosity  [default:0]
      --version           Show the version and exit.
      --help              Show this message and exit.

    Commands:
      check     Check if the hypervisor meets the requirements.
      images    Manage images.
      networks  Manage networks.
      vms       Manage virtual machines.

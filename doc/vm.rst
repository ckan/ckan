Testing CKAN in a VM
++++++++++++++++++++

.. WARNING::
  This document is still under development, use only if you are a member
  of the CKAN team who wishes to be an early adopter and are interested in
  experimenting with virtual machines.

If you aren't running Lucid, you may need to test in a VM. 

Repository cache
================

First set up a cache of the repositories so that you don't need to fetch packages each time you
build a VM:

::

    $ sudo apt-get install apt-proxy
    $ sudo apt-get install uml-utilities

Now find your local host's ethernet port name, IP address, netmask::

    $ ifconfig
    eth0      Link encap:Ethernet  HWaddr 1c:6f:65:8a:0a:d8
              inet addr:50.56.101.208  Bcast:50.56.101.255  Mask:255.255.255.0

i.e.::

    ethernet port name: eth0
    IP address: 50.56.101.208
    netmask: 255.255.255.0

These instructions assume these values, so replace them with yours.

Now edit your apt-get config::

    $ sudo vim /etc/apt-proxy/apt-proxy.conf

And set these two lines. The first is your host's IP address::

    ;; Server IP to listen on
    address = 50.56.101.208

    ;; Server port to listen on
    port = 9998

Now restart it::

    $ sudo /etc/init.d/apt-proxy restart

Once this is complete, your (empty) proxy is ready for use on
http://<host-machine-ip>:9998 and will find Ubuntu repository under ``/ubuntu``.

See also:

* https://help.ubuntu.com/community/AptProxy


VM creation
===========

Install the VM program::

    sudo apt-get install python-vm-builder
    sudo apt-get install kvm-pxe

Now create a directory ``~/Vms`` for your virtual machines.

::

    mkdir ~/Vms


We'll use manual bridging and networking rather than relying on the magic provided by ``libvirt``. Out virtual network for the VMs will be 192.168.100.xxx. You can use any number from 2-253 inclusive for the last bit of the IP. This first machine will have the IP address 192.168.100.2. Each virtual machine afterwards must have a unique IP address.

First set some variables (use your own IP address for HOST_IP):

::

    export THIS_IP="4"
    export HOST_IP="50.56.101.208"

Check your CPU has native VM support::

    $ kvm-ok

If your CPU doesn't support KVM extensions:

1. change ``kvm`` to ``qemu`` in the vmbuilder step coming up next
2. use ``/usr/bin/qemu`` instead of ``/usr/bin/kvm``

Now create the VM:

::

    cd ${HOME}/Vms
    export BASE_IP="192.168.100"
    sudo vmbuilder kvm ubuntu \
        --mem 512 \
        --cpus 6 \
        --domain ckan_${THIS_IP} \
        --dest ckan_${THIS_IP} \
        --flavour virtual \
        --suite lucid \
        --arch amd64 \
        --hostname ckan${THIS_IP} \
        --user ubuntu \
        --pass ubuntu \
        --rootpass ubuntu \
        --debug -v \
        --ip ${BASE_IP}.${THIS_IP} \
        --mask 255.255.255.0 \
        --net ${BASE_IP}.0 \
        --bcast ${BASE_IP}.255 \
        --gw ${BASE_IP}.254 \
        --dns ${BASE_IP}.254 \
        --proxy http://${HOST_IP}:9998/ubuntu \
        --components main,universe \
        --addpkg vim \
        --addpkg openssh-server \
        --addpkg wget

This assumes you already have an apt mirror set up on port 9998 as described
above and that you are putting everything in ``~/Vms``.

Now for the networking. 

First check you have forwarding enabled on the host:

::

    sudo -s 
    echo "1" > /proc/sys/net/ipv4/ip_forward
    exit

Now save this as ``~/Vms/start.sh``:

::

    #!/bin/bash

    if [ "X$1" = "X" ] || [ "X$2" = "X" ]  || [ "X$3" = "X" ] || [ "X$4" = "X" ]  || [ "X$5" = "X" ]; then
        echo "ERROR: call this script with network device name, tunnel name, amount of memory, number of CPUs and path to the image e.g." 
        echo "       $0 eth0 qtap0 512M 4 /home/Vms/ckan_2/tmpKfAdeU.qcow2 [extra args to KVM]"
        exit 1
    fi

    NETWORK_DEVICE=$1
    TUNNEL=$2
    MEM=$3
    CPUS=$4
    IMAGE=$5
    EXTRA=$6
    MACADDR="52:54:$(dd if=/dev/urandom count=1 2>/dev/null | md5sum | sed 's/^\(..\)\(..\)\(..\)\(..\).*$/\1:\2:\3:\4/')";

    echo "Creating bridge..."
    sudo iptables -t nat -A POSTROUTING -o ${NETWORK_DEVICE} -j MASQUERADE
    sudo brctl addbr br0
    sudo ifconfig br0 192.168.100.254 netmask 255.255.255.0 up
    echo "done."
    echo "Creating tunnel..."
    sudo modprobe tun
    sudo tunctl -b -u root -t ${TUNNEL}
    sudo brctl addif br0 ${TUNNEL}
    sudo ifconfig ${TUNNEL} up 0.0.0.0 promisc
    echo "done."
    echo "Starting VM ${IMAGE} on ${TUNNEL} via ${NETWORK_DEVICE} with MAC ${MACADDR}..."
    sudo /usr/bin/kvm -M pc-0.12 -enable-kvm -m ${MEM} -smp ${CPUS} -name dev -monitor pty -boot c -drive file=${IMAGE},if=ide,index=0,boot=on -net nic,macaddr=${MACADDR} -net tap,ifname=${TUNNEL},script=no,downscript=no -serial none -parallel none -usb ${EXTRA}


Make it executable:

::

    chmod a+x ~/Vms/start.sh

Now you can start it along the lines of this:

::

    ./start.sh eth0 qtap0 512M 1 /home/james/Vms/ckan_4/tmpuNIv2h.qcow2

Now login:

::

    ssh ubuntu@${BASE_IP}.${THIS_IP}

Once in you'll need some more configuration.

Edit ``/etc/resolv.conf`` to contain just this (the Google DNS servers, handy
to used a fixed IP so that you don't have to update your ``resolve.conf`` each
time you move to a different network):

::

    nameserver 8.8.8.8

Then change ``/etc/apt/apt.conf`` to comment out the proxy line, you may as
well get updates directly now.

Finally, run this (swapping the repository name for the one you want to test)
to allow yourself to install CKAN:

::

    sudo apt-get install wget
    wget -qO-  http://apt-alpha.ckan.org/packages.okfn.key | sudo apt-key add -
    echo "deb http://apt-alpha.ckan.org/debian lucid universe" | sudo tee /etc/apt/sources.list.d/okfn.list
    sudo apt-get update

Now that you have the repo added you can install and test CKAN as normal.

Here's how mine look:

::

    ubuntu@ckan4:~$ cat /etc/network/interfaces 
    # This file describes the network interfaces available on your system
    # and how to activate them. For more information, see interfaces(5).
    
    # The loopback network interface
    auto lo
    iface lo inet loopback
    
    # The primary network interface
    auto eth0
    iface eth0 inet static
            address 192.168.100.4
            netmask 255.255.255.0 
            network 192.168.100.0
            broadcast 192.168.100.255
            gateway 192.168.100.254
            dns 192.168.100.254
    ubuntu@ckan4:~$ cat /etc/resolv.conf 
    nameserver 8.8.8.8


VNC access
==========

To add ability to VNC into the VM as it runs (useful for debug), add this line to the start.sh command::

    -vnc :1

Then you can vnc to it when running using a VNC Client.
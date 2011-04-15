Packaging CKAN as Debian Files
++++++++++++++++++++++++++++++

.. note :: 

   This guide is a work in progress, please report any problems to the 
   ckan-dev mailing list.

   It will need a second draft once packaging has stabilised a bit more.

Dependencies
============

In order to pacakge CKAN and dependencies as Debian files you'll need the
following tools:

::

    sudo apt-get install -y python wget dh-make devscripts build-essential fakeroot cdbs

And depending on the source repositories of the things you are packaging you'll
probably need:

::

    sudo apt-get install -y mercurial git-core subversion


Preparation
===========

In order to build packages you'll need a directory with all of the source code
for the various packages you want to pacakge checked out in a directory. You'll
also need a copy of BuildKit installed.

The easiest way to achieve this is to set up a virtual environment with
BuildKit installed and use ``pip`` to install the dependencies in it for you.

::

    wget http://pylonsbook.com/virtualenv.py 
    python virtualenv.py missing
    cd missing
    bin/easy_install pip
    bin/pip install BuildKit

The idea is that all the dependencies you want to package are in a
``lucid_missing.txt`` file as editable requirements with exact revisions
specified. For example, if we want to package ApacheMiddleware we would have this line:

::

    -e hg+https://hg.3aims.com/public/ApacheMiddleware@c5ab5c3169a5#egg=ApacheMiddleware

Once your requirements are in place, install them like this:

::

    bin/pip install -r lucid_missing.txt

.. tip ::

   You can't just do this because pip ignores the ``-e`` for code that is
   installed from a package and fails to put it in ``src``:

   ::

       # Won't work
       -e ApacheMiddleware

   You can put the source directory manually in your virtual environment's
   ``src`` directory though if you need to though.

Automatic Packaging
===================

The BuildKit script will build and place Debian packages in your ``missing``
directory. Make sure there is nothing in there that shouldn't be overwritten by
this script.

To package everything automatically, run it like this:

::

    cd missing
    bin/python -m buildkit.update_all .

For each pacakge you'll be loaded into ``vim`` to edit the changelog. Save and
quit when you are done. Names, version numbers and dependencies are
automatically generated.

You should find all your packages nicely created now.

Manual Packaging
================

If you want more control over version numbers and dependencies or you just want
to package one thing you can do so like this:

::

    python -m buildkit.deb /path/to/virtualenv ckan-deps 1.3 http://ckan.org python-dep-1 python-dep-2 ... etc

Version Numbers
===============

To release an upgrade of a package it must have a higher version number. There
is a chance you may want to release a more recent version of a package despite
the fact the underlying version number hasn't changed. For this reason, we
always add a ``~`` character followed by a two digit number to the end of the
actual version number as specified in ``setup.py`` for the package. 

For example, the version number for CKAN may be ``1.4.0a~01``, producing a
package named ``python-ckan_1.4.0a~01_amd64.deb``.

Writing a ``ckan`` command
==========================

For packages that don't represent Python libraries it is actually easier to
build the ``.deb`` manually rather than using Debian's tools.

Create a directory named ``ckan``. Then within it create a ``DEBIAN`` directory with three files:

``control``:

    ::

        Package: ckan
        Version: 1.3.2~09
        Architecture: amd64
        Maintainer: James Gardner <james.gardner@okfn.org>
        Installed-Size: 0
        Depends: python-ckan
        Recommends: postgresql, curl
        Section: main/web
        Priority: extra
        Homepage: http://ckan.org
        Description: ckan
         The Data Hub

``postinst``:

    ::

        #!/bin/sh
        set -e
        # Any commands that happen after install or upgrade go here

``postrm``

    ::

        #!/bin/sh
        set -e
        # Any commands that happen after removal or before upgrade go here

Then in the ``ckan`` directory you add any files you want copied. In this case
we want a ``/usr/bin/ckan-create-instance`` script so we create the ``usr``
directory in the ``ckan`` directory at the same level as the ``DEBIAN``
directory, then create the ``bin`` directory within it and add the script in
there.

Finally we want to package up the ``.deb`` file. From within the ``ckan``
directory run this:

::

    dpkg-deb -b . ..

This will create the ``../ckan_1.3.2~09_amd64.deb`` package ready for you to
upload to the repo.

The ``ckan`` package is already created so in reality you will usually be
packaging ``ckan-<instance>``. If you make sure your package depends on
``ckan`` and ``python-ckanext-<instance>`` you can then call the ``ckan``
package's ``ckan-create-instance`` command in your ``ckan-<instance>``'s
``postinst`` command to set up Apache and PostgreSQL for the instance
automatically.

Setting up the Repositories
===========================

Convert a Python package installed into a virtualenv into a Debian package automatically

Usage:

::

    python -m buildkit.deb . ckanext-csw 0.3~08 http://ckan.org python-ckanext-dgu python-owslib
    python -m buildkit.deb . ckanext-dgu 0.2~06 http://ckan.org python-ckan
    python -m buildkit.deb . ckanext-qa 0.1~09 http://ckan.org python-ckan
    python -m buildkit.deb . ckan 1.3.2~10 http://ckan.org python-routes python-vdm python-pylons python-genshi python-sqlalchemy python-repoze.who python-repoze.who-plugins python-pyutilib.component.core python-migrate python-formalchemy python-sphinx python-markupsafe python-setuptools python-psycopg2 python-licenses python-ckan-deps

There's a dependency on postfix. Choose internet site and the default hostname unless you know better.

Once you have packages you'll want to put them in a repo. You can do that as described here:

* http://joseph.ruscio.org/blog/2010/08/19/setting-up-an-apt-repository/

Then add them like this:

::

    cd /var/packages/debian/
    sudo reprepro includedeb lucid ~/*.deb

You can remove them like this from the same directory:

::

    sudo reprepro remove lucid python-ckan

Testing in a VM
===============

If you aren't running Lucid, you may need to test in a VM. First set up a cache
of the repositories so that you don't need to fetch packages each time you
build a VM:

::

    sudo apt-get install apt-proxy

Once this is complete, your (empty) proxy is ready for use on
http://mirroraddress:9999 and will find Ubuntu repository under ``/ubuntu``.

See also:

* https://help.ubuntu.com/community/AptProxy

Now create a directory ``~/Vms`` for your virtual machines.

::

    mkdir ~/Vms


We'll use manual bridging and networking rather than relying on the magic provided by ``libvirt``. Out virtual network for the VMs will be 192.168.100.xxx. You can use any number from 2-253 inclusive for the last bit of the IP. This first machine will have the IP address 192.168.100.2. Each virtual machine afterwards must have a unique IP address.

First set some variables:

::

    export THIS_IP="3"
    export HOST_IP="10.10.9.99"

You can get the host IP by looking at the output from ``ifconifg``. 

Now create the VM:

::

    cd ${HOME}/Vms
    export BASE_IP="192.168.100"
    sudo vmbuilder kvm ubuntu \
        --mem 512 \
        --cpus 4 \
        --domain ckan_${THIS_IP} \
        --dest ckan_${THIS_IP} \
        --flavour virtual \
        --suite lucid \
        --arch amd64 \
        --hostname ckan_${THIS_IP} \
        --user ubuntu \
        --pass ubuntu \
        --rootpass ubuntu \
        --debug -v \
        --ip ${BASE_IP}.${THIS_IP} \
        --mask 255.255.255.0 \
        --net ${BASE_IP}.0 \
        --bcast ${BASE_IP}.255 \
        --gw ${BASE_IP}.1 \
        --dns ${BASE_IP}.1 \
        --proxy http://${HOST_IP}:9999/ubuntu \
        --components main,universe \
        --addpkg vim \
        --addpkg openssh-server 


This assumes you already have an apt mirror set up on port 9999 as described
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

Now you can start it:

::

    ./start.sh eth1 qtap0 512M 1 /home/james/Vms/ckan_3/tmpuNIv2h.qcow2

Now login:

::

    ssh ubuntu@${BASE_IP}.${THIS_IP}

Once in run this (swapping the repository name for the one you want to test):

::

    sudo apt-get install wget
    wget -qO-  http://apt-alpha.ckan.org/packages.okfn.key | sudo apt-key add -
    echo "deb http://apt-alpha.ckan.org/debian lucid universe" | sudo tee /etc/apt/sources.list.d/okfn.list
    sudo apt-get update

If you change your host machine's networking you will probably need to update
the ``/etc/resolv.conf`` in the guest.

Now that yoy have the repo added you can install and test CKAN as normal.

Relase Process
==============

For any instance of CKAN, the following release process occurs:

* Package up all the ``.deb`` files in a directory with the release date in the
  format ``yyyy-mm-dd_nn`` where ``nn`` is the release the number of the
  release on each day. eg ``2011-03-13_01``

* Import them into the dev repositoy:

  ::
  
      cd /var/packages/<instance>-dev 
      sudo reprepro includedeb lucid /home/ubuntu/release/2011-03-13_01/*.deb
  
  Here's the pool of packages after the import:
  
  ::
  
      $ cd /var/packages/<instance>-dev
      $ find . | grep ".deb"
      ./pool/universe/p/python-apachemiddleware/python-apachemiddleware_0.1.0-1_amd64.deb
      ./pool/universe/p/python-ckan/python-ckan_1.3.2~10-1_amd64.deb
      ./pool/universe/p/python-ckanext-dgu/python-ckanext-dgu_0.2~06-1_amd64.deb
      ./pool/universe/p/python-licenses/python-licenses_0.6-1_amd64.deb
      ./pool/universe/p/python-ckanclient/python-ckanclient_0.6-1_amd64.deb
      ./pool/universe/p/python-vdm/python-vdm_0.9-1_amd64.deb
      ./pool/universe/p/python-ckan-deps/python-ckan-deps_1.3.4-1_amd64.deb
      ./pool/universe/p/python-owslib/python-owslib_0.3.2beta~02-1_amd64.deb
      ./pool/universe/p/python-formalchemy/python-formalchemy_1.3.6-1_amd64.deb
      ./pool/universe/p/python-solrpy/python-solrpy_0.9.3-1_amd64.deb
      ./pool/universe/p/python-markupsafe/python-markupsafe_0.9.2-1_amd64.deb
      ./pool/universe/p/python-ckanext-qa/python-ckanext-qa_0.1~09-1_amd64.deb
      ./pool/universe/p/python-ckanext-csw/python-ckanext-csw_0.3~04-1_amd64.deb
      ./pool/universe/p/python-pyutilib.component.core/python-pyutilib.component.core_4.1-1_amd64.deb
      ./pool/universe/c/ckan/ckan_1.3.2~09_amd64.deb
      ./pool/universe/c/ckan-dgu/ckan-dgu_0.2~05_amd64.deb
  
* Test on the dev server, if everything is OK, copy the dev repo to UAT:

  ::
  
      $ cd /var/packages/
      $ sudo rm -r <instance>-uat
      $ sudo cp -pr <instance>-dev <instance>-uat

* You can now run this on UAT:

  ::

     sudo apt-get update
     sudo apt-get upgrade

  Because it is an exact copy of the dev repo at the point you tested you can
  be sure the software is the same

* If all goes well, repeat this process with staging and live repos to deploy the release.
  

Next Steps
==========

* Delayed updates




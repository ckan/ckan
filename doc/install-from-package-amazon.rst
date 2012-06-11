Setup on Amazon EC2
===================


If you prefer to run your CKAN package install in the cloud, you can use an Amazon EC2 instance, which is a fairly cheap and lightweight way to set up a server.

Create an Amazon Account
************************

If you don't already have an Amazon AWS account you'll need to create one first.  You can `create an Amazon AWS account for EC2 here <http://aws.amazon.com/ec2/>`_.

Configure EC2
*************

Once you have an EC2 account, you'll need to configure settings for your CKAN instance.

Start by logging into your `Amazon AWS Console <https://console.aws.amazon.com/s3/home>`_ and click on the EC2 tab.

Select the region you want to run your CKAN instance in - the security group you set up is region-specific. In this tutorial, we use EU West, so it will be easier to follow if you do too.

.. image :: images/1.png

Set up a Security Group
^^^^^^^^^^^^^^^^^^^^^^^

Click the **Security Groups** link in the **My Resources** section in the right-hand side of the dashboard.

.. image :: images/2.png
   :width: 807px

Create a security group called ``web_test`` that gives access to ports 22, 80 and 5000 as shown below. This is needed so that you'll actually be able to access your server once it is created. You can't change these settings once the instance is running, so you need to do so now.

.. image :: images/3a.png
   :width: 807px

.. image :: images/3b.png
   :width: 807px

Create a Keypair
^^^^^^^^^^^^^^^^

Now create a new keypair  ``ckan_test`` to access your instance:

.. image :: images/4.png
   :width: 807px

When you click **Create**, your browser will prompt you to save a keypair called ``ckan_test.pem``:

.. image :: images/5.png
   :width: 807px

In this tutorial, we save the keypair in ``~/Downloads/ckan_test.pem``, but you should save it
somewhere safe.

.. note :: If you plan to boot your EC2 instance from the command line, you need to remember where you've put this file.


Boot the EC2 Image
******************

CKAN requires Ubuntu 10.04 to run (either the i386 or amd64
architectures). Luckily Canonical provide a `range of suitable images <http://uec-images.ubuntu.com/releases/10.04/release/>`_.

The cheapest EC2 instance is the micro one, but that isn't very powerful, so in this tutorial,
we'll use the 32-bit small version.

We're in ``eu-west-1`` and we'll use an instance-only image (i.e. all the data will be lost when you shut it down) so we need the `ami-3693a542 <https://console.aws.amazon.com/ec2/home?region=eu-west-1#launchAmi=ami-3693a542>`_ AMI.

.. note ::

   There are more recent Ubuntu images at http://cloud.ubuntu.com/ami/ but we need the older 10.04 LTS release.

At this point, you can either boot this image from the AWS
console or launch it from the command line.


Option 1: Boot the EC2 Image AMI via the AWS Console
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From the EC2 dashboard, choose **Launch instance >**:

.. image :: images/2.png
  :width: 807px
  :alt: Choose launch instance from the EC2 dashboard

Now work through the wizard as shown in the following screenshots.

In the first step search for ``ami-3693a542`` and select it from the results (it may take a few seconds for Amazon to find it).

.. warning ::

   No image other than ``ami-3693a542`` will work with CKAN.

.. image :: images/i1.png
  :width: 807px
  :alt: Search for image ami-3693a542

You can keep the defaults for all of the following screens:

.. image :: images/i2.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance
.. image :: images/i3.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance
.. image :: images/i4.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance
.. image :: images/i5.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance

Choose the ``web_test`` security group you created earlier:

.. image :: images/i6.png
  :width: 807px
  :alt: Choose the web_test security group you created earlier

Then finish the wizard:

.. image :: images/i7.png
  :width: 807px
  :alt: Finish the wizard

Finally click the **View your instances on the Instances page** link:

.. image :: images/i8.png
  :width: 807px
  :alt: View your instance

After a few seconds you'll see your instance has booted. Now skip to :ref:`log-in-to-instance`.

Option 2: Boot the EC2 Image AMI from the Command Line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

[You can skip this section if you've just booted from the AWS console and go straight to :ref:`log-in-to-instance`]

To boot from the command line you still need the same information but you enter it in one command. I'll show you now.

Install The EC2 Tools Locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are on Linux, you can just install the tools like this:

::

    sudo apt-get install ec2-ami-tools
    sudo apt-get install ec2-api-tools

If you are on Windows or Mac you'll need to `download them from the Amazon website <http://aws.amazon.com/developertools/351>`_.

Once the software is installed you can use the files you've just downloaded to do create your instance.

Get Security Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~

Next click on the **Account** link, right at the top of the screen, and you'll see this screen:

.. image :: images/6.png
  :width: 807px
  :alt: The Account screen

From this screen choose **Security Credentials** from the left hand side. Once
the page has loaded scroll down and you'll see the **Access Credentials**
section. Click on the **X.509 Certificate** tab:

.. image :: images/7.png
  :width: 807px
  :alt: The Access Credentials screen

Here you'll be able to create an X.509 certificate and private key.

.. tip ::

    You can only have two X.509 certificates at any given time, so you might need
    to inactivate an old one first and then delete it before you are allowed to
    create a new one, as in the screenshot above.

Once you click the **Create New Certificate** link you get a popup which allows
you to download the certificate and private key - do this. Once again, ours are in
``~/Downloads``, but you should save it somewhere safe.

.. image :: images/8.png
  :width: 807px
  :alt: Download your certificate

.. tip ::

    Amazon will only give you a private key file once when you create it so
    although you can always go back to get a copy of the certificate, you can only
    get the private key once. Make sure you save it in a safe place.

You now have:

* Your private key (``pk-[ID].pem``)
* Your certificate file (``cert-[ID].pem``)
* Your new keypair (``ckan-test.pem``)

The private key and the certificate files have the same name in the ``ID`` part.

Create an Ubuntu Instance
~~~~~~~~~~~~~~~~~~~~~~~~~

Once the tools are installed, run this command:

::

    ec2-run-instances ami-3693a542 --instance-type m1.small --region eu-west-1 --group web_test \
        --key ckan_test \
        --private-key ~/Downloads/pk-[ID].pem \
        --cert ~/Downloads/cert-[ID].pem


.. note ::

   The ``--key`` argument is the name of the keypair (``ckan_test``), not the certificate
   itself (``ckan_test.pem``).

.. warning ::

   Amazon charge you for a minimum of one hour usage, so you shouldn't create and
   destroy lots of EC2 instances unless you want to be charged a lot.

.. _log-in-to-instance:

Log in to the Instance
**********************

Once your instance has booted, you will need to find out its public DNS. Give it
a second or two for the instance to load then browse to the running instance in
the AWS console. If you tick your instance you'll be able to find the public
DNS by scrolling down to the bottom of the **Description** tag.

.. image :: images/8a.png
  :width: 807px
  :alt: Find the public DNS

Here you can see that our public DNS is
``ec2-79-125-86-107.eu-west-1.compute.amazonaws.com``. The private DNS only works
from other EC2 instances so isn't any use to us.

Once you've found your instance's public DNS, ensure the key has the correct permissions:

::

    chmod 0600 "ckan_test.pem"

You can then log in like this:

::

    ssh -i ~/Downloads/ckan_test.pem ubuntu@ec2-79-125-86-107.eu-west-1.compute.amazonaws.com

The first time you connect you'll see this, choose ``yes``:

::

    RSA key fingerprint is 6c:7e:8d:a6:a5:49:75:4d:9e:05:2e:50:26:c9:4a:71.
    Are you sure you want to continue connecting (yes/no)? yes
    Warning: Permanently added 'ec2-79-125-86-107.eu-west-1.compute.amazonaws.com,79.125.86.107' (RSA) to the list of known hosts.

When you log in you'll see a welcome message. You can now proceed to :ref:`run-package-installer`.


.. note ::

   If this is a test install of CKAN, when you have finished using CKAN, you can shut down your EC2 instance through the AWS console.

.. warning ::

   Shutting down your EC2 instance will lose all your data. Also, Amazon charge you for a minimum usage of one hour, so don't create and  destroy lots of EC2 instances unless you want to be charged a lot!

At this point, you can proceed to :ref:`run-package-installer`.

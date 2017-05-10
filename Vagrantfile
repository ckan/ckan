# -*- mode: ruby -*-
# vi: set ft=ruby :

## Vagrantfile for CKAN development machine

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.

  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "precise64"

  # The url from where the 'config.vm.box' box will be fetched if it
  # doesn't already exist on the user's system.
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"

  # Provisioning configuration
  config.vm.provision :shell, :path => ".vagrant-scripts/setup-server.sh"

  # Network configuration
  # We just forward paster default port (5000) as port 8080 on the
  # host machine.
  config.vm.network :forwarded_port, guest: 5000, host: 8080,
    auto_correct: true
end

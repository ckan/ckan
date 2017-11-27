# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-16.04"

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine.
  config.vm.network "forwarded_port", guest: 5000, host: 5000  # CKAN paster serve
  config.vm.network "forwarded_port", guest: 8983, host: 8983  # Solr

  config.vm.provision "shell", inline: <<-SHELL
    # for file in /vagrant/contrib/vagrant/bin/??_*.sh; do
    #   bash "$file";
    # done;
  SHELL
end

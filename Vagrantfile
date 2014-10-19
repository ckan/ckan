VAGRANTFILE_API_VERSION = "2"
# set docker as the default provider
ENV['VAGRANT_DEFAULT_PROVIDER'] = 'docker'
# disable parallellism so that the containers come up in order
ENV['VAGRANT_NO_PARALLEL'] = "1"
ENV['FORWARD_DOCKER_PORTS'] = "1"

DOCKER_HOST_NAME = "dockerhost"
DOCKER_HOST_VAGRANTFILE = "contrib/vagrant/docker-host/Vagrantfile"
CKAN_HOME = "/usr/lib/ckan/default"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # define a Postgres Vagrant VM with a docker provider
  config.vm.define "postgres" do |app|
    app.vm.provider "docker" do |d|
      # use a vagrant host if required (OSX & Windows)
      d.vagrant_vagrantfile = "#{DOCKER_HOST_VAGRANTFILE}"
      d.vagrant_machine = "#{DOCKER_HOST_NAME}"
      # Build the container & run it
      d.build_dir = "contrib/docker/postgresql"
      d.build_args = ["--tag=postgres"]
      d.name = "postgres"
      d.ports = ["5432:5432"]
      d.env = {
        CKAN_PASS: "ckan_pass",
        DATASTORE_PASS: "datastore_pass",
      }
      d.has_ssh = false
    end
  end

  # define a Solr Vagrant VM with a docker provider
  config.vm.define "solr" do |app|
    app.vm.provider "docker" do |d|
      # use a vagrant host if required (OSX & Windows)
      d.vagrant_vagrantfile = "#{DOCKER_HOST_VAGRANTFILE}"
      d.vagrant_machine = "#{DOCKER_HOST_NAME}"
      # Build the container & run it
      d.build_dir = "ckan/config/solr"
      d.build_args = ["--tag=solr"]
      d.name = "solr"
      d.ports = ["8983:8983"]
      d.has_ssh = false
    end
  end

  # define a CKAN Vagrant VM with a docker provider
  config.vm.define "ckan" do |app|

    app.vm.provider "docker" do |d|
      # use a vagrant host if required (OSX & Windows)
      d.vagrant_vagrantfile = "#{DOCKER_HOST_VAGRANTFILE}"
      d.vagrant_machine = "#{DOCKER_HOST_NAME}"
      # Build the container & run it
      d.build_dir = "contrib/docker/development"
      d.build_args = ["--tag=ckan"]
      d.name = "ckan"
      d.ports = ["5000:5000", "8800:8800"]
      d.link("postgres:postgres")
      d.link("solr:solr")
      d.cmd     = ["/sbin/my_init", "--enable-insecure-key"]
    end

    app.vm.synced_folder ".", "#{CKAN_HOME}/src/ckan",
      owner: "root",
      group: "root",
      mount_options: ["dmode=775,fmode=664"],
      create: true

    app.ssh.username = "root"
    app.ssh.private_key_path = "contrib/vagrant/insecure_key"

  end

end

VOLUME_PATH="data/vdb.vdi"

Vagrant.configure(2) do |config|

  release = "alpha"

  channel = release

  version = "current"

  config.vm.box = "coreos-#{release}"

  config.vm.box_url = "https://storage.googleapis.com/#{channel}.release.core-os.net/amd64-usr/#{version}/coreos_production_vagrant.json"

  config.vm.network "private_network", ip: "192.168.33.10"

  config.vm.provider "virtualbox" do |vb|

    vb.name = "main.dev.stuartw.io"

    vb.memory = 4096

    vb.cpus = 2

    vb.check_guest_additions = false

    unless File.exist?(VOLUME_PATH)
      vb.customize [
        'createhd',
        '--filename', VOLUME_PATH,
        '--format', 'VDI',
        '--size', 60 * 1024]
    end

    vb.customize [
      'storageattach', :id,
      '--storagectl', 'IDE Controller',
      '--port', 1,
      '--device', 0,
      '--type', 'hdd',
      '--medium', VOLUME_PATH]

  end

  if Vagrant.has_plugin?("vagrant-vbguest") then

    config.vbguest.auto_update = false

  end

  config.vm.provision :shell, path: "boot.sh"

end

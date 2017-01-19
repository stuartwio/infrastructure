Vagrant.configure(2) do |config|

  release = "alpha"

  channel = release

  version = "current"

  config.vm.box = "coreos-#{release}"

  config.vm.box_url = "https://storage.googleapis.com/#{channel}.release.core-os.net/amd64-usr/#{version}/coreos_production_vagrant.json"

  config.vm.network "private_network", ip: "192.168.33.10"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "512"
    vb.cpus = "2"
    vb.check_guest_additions = false
  end

  if Vagrant.has_plugin?("vagrant-vbguest") then
    config.vbguest.auto_update = false
  end

end

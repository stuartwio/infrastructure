#!/bin/bash -xe

# Create users and groups to match docker containers, mount each home dir
cat > /etc/cloud-config.yml <<EOF
#cloud-config

coreos:

  units:

    This feels a bit messy to conditionally format
    the volume on start-up - is there a better way?
    - name: format-volume.service
      command: start
      content: |
        [Unit]
        Description=Formats the volume drive
        Requires=dev-sdb.device
        After=dev-sdb.device

        [Service]
        Type=oneshot
        RemainAfterExit=yes
        ExecStart=/bin/bash -c '( \
          /usr/bin/lsblk --fs | \
          grep --silent sdb | \
          grep --silent ext4 \
        ) || ( \
          /usr/sbin/wipefs -f /dev/sdb && \
          /usr/sbin/mkfs -t ext4 /dev/sdb \
        )'

    - name: media-volume.mount
      command: start
      content: |
        [Unit]
        Description=Mount volume to /media/volume
        Requires=dev-sdb.device
        After=dev-sdb.device

        [Mount]
        What=/dev/sdb
        Where=/media/volume
        Type=ext4

    - name: docker-jenkins-create.service
      command: start
      content: |
        [Unit]
        Description=Create Jenkins container
        After=docker.service

        [Service]
        Type=oneshot
        RemainAfterExit=yes
        ExecStart=/usr/bin/docker create \
          --volume /home/jenkins:/var/jenkins_home \
          --publish 8080:8080 \
          --publish 9999:9999 \
          --publish 9998:9998 \
          --memory-reservation 512m \
          --memory 512m \
          --memory-swap 768m \
          --cpu-shares 512 \
          --name jenkins \
          --env-file /etc/jenkins.env \
          jenkins:alpine

    - name: docker-grafana-create.service
      command: start
      content: |
        [Unit]
        Description=Create Grafana container
        After=docker.service

        [Service]
        Type=oneshot
        RemainAfterExit=yes
        ExecStart=/usr/bin/docker create \
          --volume /var/log/grafana:/var/log/grafana \
          --publish 3000:3000 \
          --memory-reservation 384m \
          --memory 384m \
          --memory-swap 512m \
          --cpu-shares 256 \
          --name grafana \
          grafana/grafana

    - name: docker-kibana-create.service
      command: start
      content: |
        [Unit]
        Description=Create Kibana container
        After=docker.service

        [Service]
        Type=oneshot
        RemainAfterExit=yes
        ExecStart=/usr/bin/docker create \
          --publish 5601:5601 \
          --memory-reservation 384m \
          --memory 384m \
          --memory-swap 512m \
          --cpu-shares 256 \
          --name kibana \
          kibana

    - name: docker-jenkins.service
      command: start
      content: |
        [Unit]
        Description=Jenkins container
        After=docker-jenkins-create.service

        [Service]
        ExecStart=/usr/bin/docker start --attach jenkins
        ExecStop=/usr/bin/docker stop jenkins

    - name: docker-grafana.service
      command: start
      content: |
        [Unit]
        Description=Grafana container
        After=docker-grafana-create.service

        [Service]
        ExecStart=/usr/bin/docker start --attach grafana
        ExecStop=/usr/bin/docker stop grafana

    - name: docker-kibana.service
      command: start
      content: |
        [Unit]
        Description=Kibana container
        After=docker-kibana-create.service

        [Service]
        ExecStart=/usr/bin/docker start --attach kibana
        ExecStop=/usr/bin/docker stop kibana

  oem:
    id: openstack
    name: Openstack
    version-id: 0.0.6
    home-url: https://www.openstack.org/
    bug-report-url: https://github.com/coreos/bugs/issues
EOF

groupadd --gid 1000 jenkins

useradd --uid 1000 \
  --home-dir /home/jenkins \
  --gid jenkins \
  --shell /sbin/nologin \
  jenkins

groupadd --gid 107 grafana

useradd --uid 104 \
  --home-dir /home/jenkins \
  --gid grafana \
  --shell /sbin/nologin \
  grafana

# Kibana group conflicts with rkt-admin group

# groupadd --gid 999 kibana
#
# useradd --uid 999 \
#   --home-dir /home/kibana \
#   --gid kibana \
#   --shell /sbin/nologin \
#   kibana

jenkins_java_opts="-Xmx384m"
jenkins_java_opts="${jenkins_java_opts} -XX:MaxMetaspaceSize=128m"
jenkins_java_opts="${jenkins_java_opts} -Dcom.sun.management.jmxremote"
jenkins_java_opts="${jenkins_java_opts} -Dcom.sun.management.jmxremote.port=9999"
jenkins_java_opts="${jenkins_java_opts} -Dcom.sun.management.jmxremote.rmi.port=9998"
jenkins_java_opts="${jenkins_java_opts} -Dcom.sun.management.jmxremote.local.only=false"
jenkins_java_opts="${jenkins_java_opts} -Dcom.sun.management.jmxremote.authenticate=false"
jenkins_java_opts="${jenkins_java_opts} -Dcom.sun.management.jmxremote.ssl=false"
jenkins_java_opts="${jenkins_java_opts} -Djava.rmi.server.hostname=192.168.33.10"

echo "JAVA_OPTS=${jenkins_java_opts}" > /etc/jenkins.env

coreos-cloudinit --from-file /etc/cloud-config.yml

# docker run \
#   --detach \
#   --restart always \
#   --volume /home/jenkins:/var/jenkins_home \
#   --publish 8080:8080 \
#   --publish 9999:9999 \
#   --publish 9998:9998 \
#   --memory-reservation 512m \
#   --memory 512m \
#   --memory-swap 768m \
#   --cpu-shares 512 \
#   --name jenkins \
#   --env "JAVA_OPTS=${java_opts}" \
#   jenkins:alpine

# ElasticSearch requires its own server

# groupadd --gid 101 elasticsearch
#
# useradd --uid 100 \
#   --home-dir /home/elasticsearch \
#   --gid elasticsearch \
#   --shell /sbin/nologin \
#   elasticsearch
#
# docker run \
#   --detach \
#   --restart always \
#   --volume /home/elasticsearch/data:/usr/share/elasticsearch/data \
#   --publish 9200:9200 \
#   --publish 9300:9300 \
#   --memory-reservation 3g \
#   --memory 3g \
#   --memory-swap 4g \
#   --cpu-shares 1024 \
#   --name elasticsearch \
#   elasticsearch:alpine

# InfluxDB should be on its own server

# docker run \
#   --detach \
#   --restart always \
#   --volume /home/influxdb:/var/lib/influxdb \
#   --publish 8083:8083 \
#   --publish 8086:8086 \
#   --memory-reservation 3g \
#   --memory 3g \
#   --memory-swap 4g \
#   --cpu-shares 1024 \
#   --name influxdb \
#   influxdb:alpine

# Logstash server should be on its own server
# Logstash forwarder required here

# docker run \
#   --detach \
#   --restart always \
#   --memory-reservation 128m \
#   --memory 128m \
#   --memory-swap 192m \
#   --cpu-shares 128 \
#   --name logstash \
#   logstash:alpine

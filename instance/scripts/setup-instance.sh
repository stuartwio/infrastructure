#!/bin/bash -x

DOCKER_REPO=stuartw.io
GIT_REPO=https://github.com/stuartwio/infrastructure.git

git clone "$GIT_REPO"

docker build --tag "$DOCKER_REPO/jenkins" /root/infrastructure/docker/jenkins
docker build --tag "$DOCKER_REPO/git" /root/infrastructure/docker/git

mkdir --parents /media/volume/home

groupadd --gid 1001 git
groupadd --gid 1000 jenkins

useradd --uid 1001 \
  --create-home \
  --skel /usr/share/skel \
  --home-dir /media/volume/home/git \
  --gid git \
  --shell /bin/bash \
  git
useradd --uid 1000 \
  --create-home \
  --skel /usr/share/skel \
  --home-dir /media/volume/home/jenkins \
  --gid jenkins \
  --shell /sbin/nologin \
  jenkins

touch /media/volume/home/git/.ssh/authorized_keys
ssh-keygen -t rsa -C jenkins -f /media/volume/home/jenkins/.ssh/id_rsa
cat /home/core/.ssh/authorized_keys >> /media/volume/home/git/.ssh/authorized_keys
cat /media/volume/home/jenkins/.ssh/id_rsa.pub >> /media/volume/home/git/.ssh/authorized_keys

git init --bare /media/volume/home/git/seed.git
chown -R git:git /media/volume/home/git/seed.git

mkdir -p /media/volume/git/etc/ssh
chown -R git:git /media/volume/git/etc/ssh

docker create \
  --volume /media/volume/git/etc/ssh:/etc/ssh \
  --volume /media/volume/home/git:/home/git \
  --memory-reservation 16m \
  --memory 16m \
  --memory-swap 16m \
  --cpu-shares 256 \
  --name git \
  --hostname git \
  stuartw.io/git
docker create \
  --volume /media/volume/home/jenkins:/var/jenkins_home \
  --link git:git \
  --publish 8080:8080 \
  --memory-reservation 768m \
  --memory 768m \
  --memory-swap 1024m \
  --cpu-shares 1024 \
  --name jenkins \
  --hostname jenkins \
  --env "JAVA_OPTS=-Dhudson.DNSMultiCast.disabled=true -Xmx512m -XX:MaxMetaspaceSize=128m" \
  stuartw.io/jenkins

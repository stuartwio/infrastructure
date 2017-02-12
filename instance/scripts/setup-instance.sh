#!/bin/bash -x

DOCKER_REPO=stuartw.io
GIT_REPO=https://github.com/stuartwio/infrastructure.git
CORE_HOME=/home/core
JENKINS_HOME=/media/volume/jenkins/home
GIT_HOME=/media/volume/git/home
GIT_SSH_HOME=/media/volume/git/ssh

git clone "$GIT_REPO"

docker build --tag "$DOCKER_REPO/jenkins" /root/infrastructure/docker/jenkins
docker build --tag "$DOCKER_REPO/git" /root/infrastructure/docker/git

groupadd --gid 1001 git
groupadd --gid 1000 jenkins

useradd --uid 1001 \
  --create-home \
  --skel /usr/share/skel \
  --home-dir "$GIT_HOME" \
  --gid git \
  --shell /bin/nologin \
  git
useradd --uid 1000 \
  --create-home \
  --skel /usr/share/skel \
  --home-dir "$JENKINS_HOME" \
  --gid jenkins \
  --shell /sbin/nologin \
  jenkins

docker run \
    --rm \
    --volume "$JENKINS_HOME:/jenkins-volume" \
    --volume "$GIT_HOME:/git-volume" \
    --volume "$GIT_SSH_HOME:/etc/ssh" \
    --name setup \
    alpine setup /bin/sh -xc "apk update && apk add openssh"

sed -i 's/#\?PasswordAuthentication\b.*/PasswordAuthentication no/' "$GIT_SSH_HOME/sshd_config"
sed -i 's/#\?ChallengeResponseAuthentication\b.*/ChallengeResponseAuthentication no/' "$GIT_SSH_HOME/sshd_config"
sed -i 's/#\?PermitRootLogin\b.*$/PermitRootLogin no/' "$GIT_SSH_HOME/sshd_config"

if [[ ! -f "$GIT_SSH_HOME/ssh_host_rsa_key" ]] ; then
    ssh-keygen -N '' -t rsa -f "$GIT_SSH_HOME/ssh_host_rsa_key"
fi

if [[ ! -f "$GIT_SSH_HOME/ssh_host_dsa_key" ]] ; then
    ssh-keygen -N '' -t dsa -f "$GIT_SSH_HOME/ssh_host_dsa_key"
fi

if [[ ! -f "$GIT_SSH_HOME/ssh_host_ecdsa_key" ]] ; then
    ssh-keygen -N '' -t ecdsa -f "$GIT_SSH_HOME/ssh_host_ecdsa_key"
fi

if [[ ! -f "$GIT_SSH_HOME/ssh_host_ed25519_key" ]] ; then
    ssh-keygen -N '' -t ed25519 -f "$GIT_SSH_HOME/ssh_host_ed25519_key"
fi

if [[ ! -d "$GIT_HOME/.ssh" ]] ; then
    mkdir "$GIT_HOME/.ssh"
fi

if [[ ! -f "$GIT_HOME/.ssh/authorized_keys" ]] ; then
    touch "$GIT_HOME/.ssh/authorized_keys"
    cat "$CORE_HOME/.ssh/authorized_keys" >> "$GIT_HOME/.ssh/authorized_keys"
fi

if [[ ! -d "$JENKINS_HOME/.ssh" ]] ; then
    mkdir "$JENKINS_HOME/.ssh"
fi

if [[ ! -f "$JENKINS_HOME/.ssh/id_rsa" ]] ; then
    ssh-keygen -t rsa -N "" -C jenkins -f "$JENKINS_HOME/.ssh/id_rsa"
    cat "$JENKINS_HOME/.ssh/id_rsa.pub" >> "$GIT_HOME/.ssh/authorized_keys"
fi

if [[ ! -d "$GIT_HOME/seed.git" ]] ; then
    git init --bare "$GIT_HOME/seed.git"
fi

docker create \
  --volume "$GIT_SSH_HOME:/etc/ssh" \
  --volume "$GIT_HOME:/home/git" \
  --memory-reservation 16m \
  --memory 16m \
  --memory-swap 16m \
  --cpu-shares 256 \
  --name git \
  --hostname git \
  stuartw.io/git
docker create \
  --volume "$JENKINS_HOME:/var/jenkins_home" \
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

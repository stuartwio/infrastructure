#!/bin/bash -x

DOCKER_REPO=stuartw.io
GIT_REPO=https://github.com/stuartwio/infrastructure.git

git clone "$GIT_REPO"

docker build --tag "$DOCKER_REPO/jenkins" /root/infrastructure/docker/jenkins
docker build --tag "$DOCKER_REPO/git" /root/infrastructure/docker/git

groupadd --gid 1001 git
groupadd --gid 1000 jenkins

useradd --uid 1001 \
  --create-home \
  --home-dir /home/git \
  --gid git \
  --shell /bin/nologin \
  git
useradd --uid 1000 \
  --create-home \
  --home-dir /home/jenkins \
  --gid jenkins \
  --shell /sbin/nologin \
  jenkins

if [[ ! -d /var/lib/docker/volumes/jenkins-volume ]] ; then
    docker volume create \
        --driver local \
        --name jenkins-volume
fi

if [[ ! -d /var/lib/docker/volumes/git-volume ]] ; then
    docker volume create \
        --driver local \
        --name git-volume
fi

docker create \
    --interactive \
    --volume git-volume:/git-volume \
    --volume jenkins-volume:/jenkins-volume \
    --name setup \
    alpine /bin/sh

docker start setup
docker exec setup /bin/sh -xc "apk update && apk add openssh"

if docker exec setup /bin/sh -xc "[[ ! -d /git-volume/.ssh ]]" ; then
    docker exec setup /bin/sh -xc "mkdir /git-volume/.ssh"
fi

if docker exec setup /bin/sh -xc "[[ ! -f /git-volume/.ssh/authorized_keys ]]" ; then
    docker exec setup /bin/sh -xc "touch /git-volume/.ssh/authorized_keys"
    cat /home/core/.ssh/authorized_keys | docker exec setup /bin/sh -xc "cat - >> /git-volume/.ssh/authorized_keys"
fi

if docker exec setup /bin/sh -xc "[[ ! -d /jenkins-volume/.ssh ]]" ; then
    docker exec setup /bin/sh -xc "mkdir /jenkins-volume/.ssh"
fi

if docker exec setup /bin/sh -xc "[[ ! -f /jenkins-volume/.ssh/id_rsa ]]" ; then
    docker exec setup /bin/sh -xc "ssh-keygen -t rsa -N "" -C jenkins -f /jenkins-volume/.ssh/id_rsa"
    docker exec setup /bin/sh -xc "cat /jenkins-volume/.ssh/id_rsa.pub >> /git-volume/.ssh/authorized_keys"
fi

if docker exec setup /bin/sh -xc "[[ ! -d /git-volume/seed.git ]]" ; then
    docker exec setup /bin/sh -xc "git init --bare /git-volume/seed.git"
fi

docker stop setup
docker rm setup

docker create \
  --volume /etc/ssh:/etc/ssh \
  --volume git-volume:/home/git \
  --memory-reservation 16m \
  --memory 16m \
  --memory-swap 16m \
  --cpu-shares 256 \
  --name git \
  --hostname git \
  stuartw.io/git
docker create \
  --volume jenkins-volume:/var/jenkins_home \
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

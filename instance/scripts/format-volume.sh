#!/bin/bash -x

# Devices
DEV=/dev/xvdk
JENKINS_HOME_DEV_PART=/dev/xvdk1
GIT_HOME_DEV_PART=/dev/xvdk2
GIT_SSH_DEV_PART=/dev/xvdk3

# Label
JENKINS_HOME_LABEL=JENKINS-HOME
GIT_HOME_LABEL=GIT-HOME
GIT_SSH_HOME_LABEL=GIT-SSH

# Filesystem
FS="ext4"

if ! parted  --script --machine /dev/xvdk print ; then
    echo "Partitioning $DEV and formatting $JENKINS_HOME_DEV_PART, $GIT_HOME_DEV_PART, $GIT_SSH_DEV_PART"
    parted --script --machine "$DEV" mklabel gpt
    parted --script --machine --align=opt "$DEV" mkpart primary "$FS" 0% 40%
    parted --script --machine --align=opt "$DEV" mkpart primary "$FS" 40% 80%
    parted --script --machine --align=opt "$DEV" mkpart primary "$FS" 80% 100%
    mkfs.ext4 -L "$JENKINS_HOME_LABEL" "$JENKINS_HOME_DEV_PART"
    mkfs.ext4 -L "$GIT_HOME_LABEL" "$GIT_HOME_DEV_PART"
    mkfs.ext4 -L "$GIT_SSH_HOME_LABEL" "$GIT_SSH_DEV_PART"
elif parted  --script --machine /dev/xvdk print | grep --silent '^1' && \
     parted  --script --machine /dev/xvdk print | grep --silent '^2' && \
     parted  --script --machine /dev/xvdk print | grep --silent '^3' ; then
    echo "Device $DEV already partitioned and \
        $JENKINS_HOME_DEV_PART, $GIT_HOME_DEV_PART, $GIT_SSH_DEV_PART partitions already formatted"
else
    >&2 echo "Device $DEV incorrectly partitioned!"
    >&2 parted  --script --machine /dev/xvdk print
    exit 1
fi

#!/bin/bash -x

# Devices
DEV="/dev/xvdk"
DEV_PART="/dev/xvdk1"
DEV_NAME="xvdk1"

# Label
LABEL="DOCKER-VOLUMES"

# Filesystem
FS="ext4"

# TODO: Handle errors

if ! lsblk --fs | grep "$DEV_NAME" | grep --silent "$FS"
then
    echo "Partitioning $DEV and formatting $DEV_PART"
    parted --script --machine "$DEV" mklabel gpt
    parted --script --machine --align=opt "$DEV" mkpart primary "$FS" 0% 100%
    mkfs.ext4 -L "$LABEL" "$DEV_PART"
else
    echo "Device partition $DEV_PART already formatted"
fi

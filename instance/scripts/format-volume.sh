#!/bin/bash -x

# Devices
DEV="/dev/xvdk"
DEV_PART="/dev/xvdk1"
DEV_NAME="xvdk1"

# Label
LABEL="VOL-A"

# Filesystem
FS="ext4"

# TODO: Handle errors

if ! lsblk --fs | grep "$DEV_NAME" | grep --silent "$FS"
then
    echo "Partitioning $DEV and formatting $DEV_PART"
    parted "$DEV" mklabel gpt
    parted --align=opt "$DEV" mkpart primary "$FS" 0% 100%
    mkfs.ext4 -L "$LABEL" "$DEV_PART"
else
    echo "Device partition $DEV_PART already formatted"
fi

#!/bin/sh

if [[ ! -f /etc/ssh/ssh_host_rsa_key ]] ; then
    ssh-keygen -N '' -t rsa -f /etc/ssh/ssh_host_rsa_key
fi

if [[ ! -f /etc/ssh/ssh_host_dsa_key ]] ; then
    ssh-keygen -N '' -t dsa -f /etc/ssh/ssh_host_dsa_key
fi

if [[ ! -f /etc/ssh/ssh_host_ecdsa_key ]] ; then
    ssh-keygen -N '' -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key
fi

if [[ ! -f /etc/ssh/ssh_host_ed25519_key ]] ; then
    ssh-keygen -N '' -t ed25519 -f /etc/ssh/ssh_host_ed25519_key
fi

exec /usr/sbin/sshd -D

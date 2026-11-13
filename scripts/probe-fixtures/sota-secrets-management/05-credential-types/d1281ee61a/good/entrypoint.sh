#!/bin/sh
# Near miss: keys generated per container at start, not baked into the image.
ssh-keygen -A
exec /usr/sbin/sshd -D

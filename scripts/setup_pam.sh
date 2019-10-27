#!/bin/bash
if [ $# -eq 0 ]; then
    echo "Provide username which will be given shadow access to run this application"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

usermod -a -G shadow $1
getent group sftpusers || groupadd sftpusers
echo "sftpusers" > /etc/sftplogin.group.allowed
cp $DIR/sftplogin /etc/pam.d

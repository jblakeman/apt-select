#!/bin/sh

apt="/etc/apt"
if [ "$PWD" = "$apt" ]; then
    echo "Please run the update from a directory other than '$apt'"
    exit 1
else
    file="sources.list"
    if [ -f "$file" ]; then
        sudo mv ${apt}/$file ${apt}/${file}.backup && \
        sudo mv $file ${apt}/$file
    else
        echo "File '$file' must exist in the current directory"
        exit 1
    fi
fi

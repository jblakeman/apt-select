#!/bin/sh

apt="/etc/apt"
file="sources.list"
apt_file=${apt}/${file}
backup=${apt_file}.backup

update (){
    sudo mv $apt_file $backup  &&
    sudo mv $file $apt_file &&
    echo "apt has been updated"
    exit 0
}

isBackup (){
    local query options answer
    query="Copied original file '$backup' exists.\nOverwrite?"
    options="Options:\n[y] for yes\n[n] for no "
    if [ -z "$1" ]; then
        echo -en "$query\n$options"
    else
        echo -en "$options"
    fi
    read answer
    case $answer in 
        y) update;;
        n) echo "apt not updated";;
        *) isBackup 1;;
    esac
}

if [ "$PWD" = "$apt" ]; then
    echo "Please run the update from a directory other than '$apt'"
    exit 1
else
    if [ -f "$file" ]; then
        [ -f "$backup" ] && isBackup || update
    else
        echo "File '$file' must exist in the current directory"
        exit 1
    fi
fi

#!/bin/bash

apt="/etc/apt"
file="sources.list"
apt_file=${apt}/${file}
backup=${apt_file}.backup

needSudo (){
    if [ $EUID -ne 0 ]; then
        echo "$0 needs sudoer priveleges to modify '${apt_file}'"
        echo "Enter sudo password to continue"
    fi
}

updateApt (){
    sudo mv $file $apt_file && echo "apt has been updated"
}

updateBackup (){
    sudo mv $apt_file $backup && echo "Current file backed up to '$backup'" &&
    updateApt
    exit 0
}

isBackup (){
    local query options opt
    query="A backup file already exists.\n"
    query+="Choose one of the following options:\n"
    echo -e "$query"
    options=(
        "Replace current backup"
        "Replace 'sources.list' without backing up"
        "Quit"
    )
    select opt in "${options[@]}"
    do
        case $opt in
            "${options[0]}")
                needSudo
                updateBackup
                break
                ;;
            "${options[1]}")
                needSudo
                updateApt
                break
                ;;
            "${options[2]}")
                break
                ;;
            *) echo invalid option;;
        esac
    done
}

if [ "$PWD" = "$apt" ]; then
    echo "Please run the update from a directory other than '$apt'"
    exit 1
else
    if [ -f "$file" ]; then
        if [ -f "$backup" ]; then
            isBackup
        else
            needSudo && updateBackup
        fi
    else
        echo "File '$file' must exist in the current directory"
        exit 1
    fi
fi

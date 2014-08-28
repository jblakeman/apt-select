#!/bin/bash

apt=/etc/apt
file=sources.list
apt_file=${apt}/${file}
backup=${apt_file}.backup

if [ $EUID -ne 0 ]; then
    echo -e "$0 needs sudoer priveleges to modify ${apt_file}"
    sudo -K
    sudo -v || exit $?
fi

updateApt (){
    sudo mv $file $apt_file &&
    echo "apt has been updated"
}

updateBackup (){
    sudo mv $apt_file $backup &&
    echo "$apt_file backed up to $backup"
    updateApt
}

isBackup (){
    local query options opt
    query="Backup file $backup already exists.\n"
    query+="Choose one of the following options:"
    echo -e "$query"
    options=(
        "Replace backup and update apt"
        "Update apt without backing up"
        "Examine backup file"
        "Examine $apt_file"
        "Examine $file"
        "Quit"
    )
    select opt in "${options[@]}"
    do
        case $opt in
            "${options[0]}")
                updateBackup
                break
                ;;
            "${options[1]}")
                updateApt
                break
                ;;
            "${options[2]}")
                less $backup
                ;;
            "${options[3]}")
                less $apt_file
                ;;
            "${options[4]}")
                less $file
                ;;
            "${options[5]}")
                break
                ;;
            *) echo invalid option;;
        esac
    done
}

if [ "$PWD" = "$apt" ]; then
    echo "Please run the update from a directory other than $apt"
    exit 1
else
    if [ -f "$file" ]; then
        if [ -f "$backup" ]; then
            isBackup
        else
            updateBackup
        fi
    else
        echo "$file must exist in the working directory"
        exit 1
    fi
fi
sudo -k
exit 0

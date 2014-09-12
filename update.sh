#!/bin/bash

apt=/etc/apt
file=sources.list
apt_file=${apt}/${file}
backup=${apt_file}.backup

if [ $EUID -ne 0 ]; then
    echo "$0 needs sudoer priveleges to modify ${apt_file}"
    if ! awk -F: -v u="$USER" '
             /^sudo/ {
                for(i=4;i<=NF;i++) {
                    if($i==u) {
                        f=1
                        break
                    }
                }
             } END {
                if(!f)
                    exit 1
            }' /etc/group; then
        echo "Sorry, user $USER may not run sudo on $(hostname)."
        exit 1
    else
        echo "please run script as super user (root)"
        exit 1
    fi
fi

updateApt (){
    mv $file $apt_file &&
    echo "apt has been updated"
}

updateBackup (){
    mv $apt_file $backup &&
    echo "$apt_file backed up to $backup"
    updateApt
}

examine (){
    less $1 2>/dev/null
    isBackup
    break
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
                examine $backup
                ;;
            "${options[3]}")
                examine $apt_file
                ;;
            "${options[4]}")
                examine $file
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
exit 0

#!/usr/bin/env bash

declare -r APT_DIR_PATH='/etc/apt'
declare -r APT_SOURCES_FILE_NAME='sources.list'
declare -r APT_SOURCES_FILE_PATH="${APT_DIR_PATH}/${APT_SOURCES_FILE_NAME}"
declare -r APT_SOURCES_BACKUP_FILE_PATH="${APT_SOURCES_FILE_PATH}.backup"

# shellcheck disable=SC2046
if [ $(id -u) -ne 0 ]; then
    echo "${0} needs root privilege to modify ${APT_SOURCES_FILE_PATH}"
    echo "please run script as super user (root)"
    exit 1
fi

update_apt (){
    mv "${APT_SOURCES_FILE_NAME}" "${APT_SOURCES_FILE_PATH}" &&
    echo "APT_DIR_PATH has been updated"
}

update_backup (){
    mv "${APT_SOURCES_FILE_PATH}" "${APT_SOURCES_BACKUP_FILE_PATH}" &&
    echo "${APT_SOURCES_FILE_PATH} backed up to ${APT_SOURCES_BACKUP_FILE_PATH}"
    update_apt
}

examine (){
    less "${1}" 2>/dev/null
    is_backup
}

is_backup (){
    local query options opt
    query="Backup APT_SOURCES_FILE_NAME ${APT_SOURCES_BACKUP_FILE_PATH} already exists.\n"
    query+="Choose one of the following options:"
    echo -e "${query}"
    options=(
        "Replace backup and update apt"
        "Update apt without backing up"
        "Examine ${APT_SOURCES_BACKUP_FILE_PATH}"
        "Examine ${APT_SOURCES_FILE_PATH}"
        "Examine ${PWD}/${APT_SOURCES_FILE_NAME}"
        "Quit"
    )
    select opt in "${options[@]}"; do
        case ${opt} in
            "${options[0]}")
                update_backup
                break
                ;;
            "${options[1]}")
                update_apt
                break
                ;;
            "${options[2]}")
                examine "${APT_SOURCES_BACKUP_FILE_PATH}"
                ;;
            "${options[3]}")
                examine "${APT_SOURCES_FILE_PATH}"
                ;;
            "${options[4]}")
                examine "${APT_SOURCES_FILE_PATH}"
                ;;
            "${options[5]}")
                break
                ;;
            *)
                echo invalid option
                ;;
        esac
    done
}

if [ "${PWD}" = "${APT_DIR_PATH}" ]; then
    echo "Please run the update from a directory other than ${APT_DIR_PATH}"
    exit 1
else
    if [ -f "${APT_SOURCES_FILE_NAME}" ]; then
        if [ -f "${APT_SOURCES_BACKUP_FILE_PATH}" ]; then
          is_backup
        else
          update_backup
        fi
    else
        echo "${APT_SOURCES_FILE_NAME} must exist in the working directory"
        exit 1
    fi
fi
exit 0

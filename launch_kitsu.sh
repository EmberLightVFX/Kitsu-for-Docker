#!/bin/bash

# Colors for terminal
RST='\033[0m' # Text Reset

# Regular Colors
Black='\033[0;30m'  # Black
Red='\033[0;31m'    # Red
Green='\033[0;32m'  # Green
Yellow='\033[0;33m' # Yellow
Blue='\033[0;34m'   # Blue
Purple='\033[0;35m' # Purple
Cyan='\033[0;36m'   # Cyan
White='\033[0;37m'  # White

# Bold
BBlack='\033[1;30m'  # Black
BRed='\033[1;31m'    # Red
BGreen='\033[1;32m'  # Green
BYellow='\033[1;33m' # Yellow
BBlue='\033[1;34m'   # Blue
BPurple='\033[1;35m' # Purple
BCyan='\033[1;36m'   # Cyan
BWhite='\033[1;37m'  # White

# Bold High Intensity
BIBlack='\033[1;90m'  # Black
BIRed='\033[1;91m'    # Red
BIGreen='\033[1;92m'  # Green
BIYellow='\033[1;93m' # Yellow
BIBlue='\033[1;94m'   # Blue
BIPurple='\033[1;95m' # Purple
BICyan='\033[1;96m'   # Cyan
BIWhite='\033[1;97m'  # White

# Main
main() {

    # Get latest version
    if [[ ${KITSU_VERSION,,} == "latest" ]]; then
        echo -e "${YELLOW}Checking what's the latest version of Kitsu is.${RST}"
        export KITSU_VERSION=$(curl https://api.github.com/repos/cgwire/kitsu/commits | jq -r '.[].commit.message | select(. | test("[0-9]+(\\\\.[0-9]+)+"))?' | grep -m1 "")
        if [[ ${KITSU_VERSION} == "" ]]; then
            export KITSU_VERSION="null"
        fi

        if [[ ${KITSU_VERSION} == "null"]]; then
            echo -e "${BIRed}Github API rate limit exceeded. Can't check for later versions. Please try again later${RST}"
            echo -e "${BIRed}Will launch with the old version. If you want to update, please set the wanted version on ${YELLOW}KITSU_VERSION${RST}"
        else
            echo -e "Setting KITSU_VERSION to ${Green}$KITSU_VERSION${RST}"
        fi
    fi

    export install=false
    if [ -f "/opt/kitsu/dist/.version.txt" ]; then
        echo -e "${BIGreen}Kitsu already installed${RST}"
        # Get the installed version:
        export version=$(<kitsu/dist/.version.txt)
        if [[ ${KITSU_VERSION} != "$version" && ${KITSU_VERSION} != "null" ]]; then
            echo -e "${BIYellow}The current installed version runs $version while you're requesting $KITSU_VERSION.${RST}"
            echo -e "${BIYellow}Will remove the old version and download the requested version.${RST}"
            export install=true
        fi
    else
        if [[ ${KITSU_VERSION} == "null" ]]; then
            echo -e "${BIRed}Kitsu NOT INSTALLED. Can't launch.${RST}"
        else
            echo -e "${BIYellow}Kitsu NOT INSTALLED. Installing...${RST}"
            export install=true
        fi
    fi

    if [ "$install" = true ]; then
        # Download Kitsu
        cd /opt/
        shopt -s dotglob
        rm -rf kitsu/*
        git clone -b "$KITSU_VERSION-build" --single-branch --depth 1 https://github.com/cgwire/kitsu kitsu
        echo -e "${BIGreen}Kitsu installed.${RST}"
    fi
}

main

nginx -g 'daemon off;'

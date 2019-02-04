#!/bin/bash

docker -v

if [ "$?" -ne 0 ]
then
	echo "Installing docker"
        #Change it to install a specific version
        sudo apt-get update && sudo apt-get install docker-ce
	
	if [ "$?" -eq 0 ]
	then
        	echo "docker installed successfully"
	else
    		echo "docker installation failed"
		exit 1
	fi
fi

docker pull jenkinsci/blueocean
docker run -p 8080:8080 jenkinsci/blueocean

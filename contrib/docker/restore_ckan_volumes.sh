#!/bin/bash

if [[ $1 == "-h" || $1 == "--help" ]]; then
    echo "Usage: restore_ckan_volumes.sh [BACKUP_TAG] [LOCAL_BACKUP_PATH] [CKAN_CONTAINER] [TEMP_CONTAINER_IMAGE]"
    echo "Restores CKAN volume contents from the TAR files stored in a sub-directory of LOCAL_BACKUP_PATH denoted by BACKUP_TAG"
    echo "  CKAN_CONTAINER default is \"ckan\""
    echo "  LOCAL_BACKUP_PATH default is the current directory"
    echo "  TEMP_CONTAINER_IMAGE default is \"ubuntu\""
    
    exit
fi

# Root directory in the temporary container to dump CKAN backups into
BACKUP_ROOT="/ckan_backup"

BACKUP_TAG=$1
LOCAL_BACKUP_PATH=$2
CKAN_CONTAINER=$3
TEMP_CONTAINER_IMAGE=$4

if [ ! $CKAN_CONTAINER ]; then
	CKAN_CONTAINER="ckan"
    echo "No source container specified, defaulting to \"$CKAN_CONTAINER\""
fi;

if [ ! $LOCAL_BACKUP_PATH ]; then
	LOCAL_BACKUP_PATH=$(pwd)
    echo "No destination path specified, defaulting to $LOCAL_BACKUP_PATH"
else
    LOCAL_BACKUP_PATH=`realpath $LOCAL_BACKUP_PATH`
fi;

if [ ! $TEMP_CONTAINER_IMAGE ]; then
	TEMP_CONTAINER_IMAGE="ubuntu"
    echo "No image specified for temporary container, defaulting to \"$TEMP_CONTAINER_IMAGE\""
fi;

echo "Restoring From: $BACKUP_ROOT/$BACKUP_TAG"
echo "Attaching to volumes from container: $CKAN_CONTAINER"
echo "Dumping contents to: $LOCAL_BACKUP_PATH"
echo "Using image: $TEMP_CONTAINER_IMAGE"

sudo docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar xvf $BACKUP_ROOT/$BACKUP_TAG/ckan_home.tar --directory /
sudo docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar xvf $BACKUP_ROOT/$BACKUP_TAG/ckan_config.tar --directory /
sudo docker run --rm --volumes-from $CKAN_CONTAINER -v $LOCAL_BACKUP_PATH:$BACKUP_ROOT $TEMP_CONTAINER_IMAGE tar xvf $BACKUP_ROOT/$BACKUP_TAG/ckan_storage.tar --directory /

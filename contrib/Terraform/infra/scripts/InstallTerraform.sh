#!/bin/sh

echo "**** install terraform ****"

sudo apt-get update && sudo apt-get install unzip && wget https://releases.hashicorp.com/terraform/0.11.10/terraform_0.11.10_linux_amd64.zip && unzip terraform_0.11.10_linux_amd64.zip && sudo mv terraform /usr/local/bin/ && terraform --version

FROM phusion/baseimage:0.9.15
MAINTAINER Open Knowledge

# set UTF-8 locale
RUN locale-gen en_US.UTF-8 && \
    echo 'LANG="en_US.UTF-8"' > /etc/default/locale

RUN apt-get -qq update

# Install required packages
RUN DEBIAN_FRONTEND=noninteractive apt-get -qq -y install curl

RUN curl -sSL https://get.docker.com/ | sh
RUN curl -L https://github.com/docker/fig/releases/download/1.0.0/fig-`uname -s`-`uname -m` > /usr/local/bin/fig; chmod +x /usr/local/bin/fig
ENV DOCKER_HOST unix:///docker.sock

WORKDIR /src
CMD ["/bin/bash"]

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# ==============================================================================
# Usage:
# from your source directory
#
# docker build --tag="fig_container" ckan/contrib/docker/fig
#
# docker run -it -d --name="fig-cli" --hostname="fig-cli" -p 2375 -v /var/run/docker.sock:/docker.sock -v $(pwd):/src fig_container
#
# copy the fig definition to your source directory
#
# cp ckan/contrib/docker/development/fig.yml .
#
# set the source volume path to yours
#
## bring it back up
# docker exec -it fig-cli fig up
#
## stop it
# docker exec -it fig-cli fig stop
#
## delete the containers
# docker exec -it fig-cli fig rm
#
## Build new images
# docker exec -it fig-cli fig build
#
# ==============================================================================

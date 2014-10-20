FROM phusion/baseimage:0.9.13
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
CMD ["fig", "up"]

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


# ==============================================================================
# Usage:
# docker build --tag="fig" .
# docker run --name="fig" -t -p 2375 -v /var/run/docker.sock:/docker.sock -v /path/to/src:/src fig
# ==============================================================================

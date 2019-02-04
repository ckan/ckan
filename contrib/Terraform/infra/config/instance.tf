provider "aws" {
  access_key = "${var.AWS_ACCESS_KEY_ID}"
  secret_key = "${var.AWS_SECRET_ACCESS_KEY}"
  region     = "${var.aws_region}"
}

resource "aws_instance" "ckan_server" {
  ami                    = "${data.aws_ami.ubuntu.id}"
  instance_type          = "t2.micro"
  vpc_security_group_ids = ["${aws_security_group.ckan_sg.id}"]
  associate_public_ip_address = true
  key_name               =  "ragha"
  associate_public_ip_address = true

  tags {
    Name = "${var.instance_name}-dev"
  }
}

resource "aws_security_group" "ckan_sg" {
  name = "${var.instance_name}"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = "${var.ssh_port}"
    to_port   = "${var.ssh_port}"
    protocol  = "tcp"

    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = "${var.http_port}"
    to_port   = "${var.http_port}"
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = "${var.solr_port}"
    to_port   = "${var.solr_port}"
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "null_resource" "ckan_provisioner" {
  triggers {
    public_ip = "${aws_instance.ckan_server.public_ip}"
  }

  connection {
    type = "ssh"
    host = "${aws_instance.ckan_server.public_ip}"
    user = "${var.ssh_user}"
    port = "${var.ssh_port}"
    agent = false
    private_key = "${file("/home/ubuntu/ragha.pem")}"
  }

  provisioner "file" {
    source      = "../scripts"
    destination = "~"
  }

  provisioner "file" {
    source      = "../resources"
    destination = "~"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod 711 /home/ubuntu/scripts/*",
      "/home/ubuntu/scripts/installUtil.sh",
      "/home/ubuntu/scripts/installPythonUtil.sh",
      "/home/ubuntu/scripts/installPG.sh",
      "/home/ubuntu/scripts/installRedis.sh",
      "/home/ubuntu/scripts/setUpCKAN.sh",
      "/home/ubuntu/scripts/setupPG.sh",
      "/home/ubuntu/scripts/configureCKAN.sh",
      "/home/ubuntu/scripts/installSolr.sh",
      "/home/ubuntu/scripts/linkWho.sh",
      "/home/ubuntu/scripts/createDatabase.sh",
    ]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "image-type"
    values = ["machine"]
  }

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-*"]
  }
}
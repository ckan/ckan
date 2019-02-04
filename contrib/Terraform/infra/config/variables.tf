variable "AWS_ACCESS_KEY_ID" {
  description = "The EC2 Key access."
  default = "xxxxxx"
}

variable "AWS_SECRET_ACCESS_KEY" {
  description = "The EC2 Key secret access."
  default = "xxxxxxx"
}

variable "aws_region" {
  description = "The AWS region to deploy into"
  default     = "us-west-2"
}

variable "instance_name" {
  description = "The Name tag to set for the EC2 Instance."
  default     = "ckan-test"
}

variable "ssh_port" {
  description = "The port for SSH requests."
  default     = 22
}

variable "solr_port" {
  description = "The port for SSH requests."
  default     = 8983
}

variable "http_port" {
  description = "The port http requests."
  default     = 5000
}

variable "ssh_user" {
  description = "SSH user name to use for remote exec connections,"
  default     = "ubuntu"
}

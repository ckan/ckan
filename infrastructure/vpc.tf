/*
# vpc

A terraform module to create a vpc to build on top of
*/

variable "vpc_name" {}
variable "region" {}
variable "vpc_availability_zones" {}

provider "aws" {
  region = var.region
}

data "aws_security_group" "default" {
  name = "default"
  vpc_id = module.vpc.vpc_id
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = var.vpc_name

  cidr = "10.10.0.0/16"

  azs = var.vpc_availability_zones
  private_subnets = [
    "10.10.1.0/24",
    "10.10.2.0/24",
    "10.10.3.0/24"]
  public_subnets = [
    "10.10.11.0/24",
    "10.10.12.0/24",
    "10.10.13.0/24",]
  database_subnets = [
    "10.10.21.0/24",
    "10.10.22.0/24",
    "10.10.23.0/24"]
  # elasticache_subnets = ["10.10.31.0/24", "10.10.32.0/24", "10.10.33.0/24"]
  # redshift_subnets    = ["10.10.41.0/24", "10.10.42.0/24", "10.10.43.0/24"]
  # intra_subnets       = ["10.10.51.0/24", "10.10.52.0/24", "10.10.53.0/24"]

  enable_dns_hostnames = true
  enable_dns_support = true

  create_database_subnet_group = true
  create_database_subnet_route_table = true
  create_database_internet_gateway_route = true

  tags = {
    Owner = "user"
    Environment = "staging"
  }

}

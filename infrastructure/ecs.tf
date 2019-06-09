provider "aws" {
  region = "eu-west-1"
}

locals {
  name        = "complete-ecs"
  environment = "dev"

  # This is the convention we use to know what belongs to each other
  ec2_resources_name = "${local.name}-${local.environment}"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 2.0"

  name = local.name

  cidr = "10.1.0.0/16"

  azs             = ["eu-west-1a", "eu-west-1b"]
  private_subnets = ["10.1.1.0/24", "10.1.2.0/24"]
  public_subnets  = ["10.1.11.0/24", "10.1.12.0/24"]

  enable_nat_gateway = false # this is faster, but should be "true" for real

  tags = {
    Environment = local.environment
    Name        = local.name
  }
}

#----- ECS --------
module "ecs" {
  source = "../../"
  name   = local.name
}

module "ec2-profile" {
  source = "../../modules/ecs-instance-profile"
  name   = local.name
}

#----- ECS  Services--------

module "hello-world" {
  source     = "./service-hello-world"
  cluster_id = module.ecs.this_ecs_cluster_id
}

#----- ECS  Resources--------

#For now we only use the AWS ECS optimized ami <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html>
data "aws_ami" "amazon_linux_ecs" {
  most_recent = true

  owners = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn-ami-*-amazon-ecs-optimized"]
  }

  filter {
    name   = "owner-alias"
    values = ["amazon"]
  }
}

module "this" {
  source  = "terraform-aws-modules/autoscaling/aws"
  version = "~> 3.0"

  name = local.ec2_resources_name

  # Launch configuration
  lc_name = local.ec2_resources_name

  image_id             = data.aws_ami.amazon_linux_ecs.id
  instance_type        = "t2.micro"
  security_groups      = [module.vpc.default_security_group_id]
  iam_instance_profile = module.ec2-profile.this_iam_instance_profile_id
  user_data            = data.template_file.user_data.rendered

  # Auto scaling group
  asg_name                  = local.ec2_resources_name
  vpc_zone_identifier       = module.vpc.private_subnets
  health_check_type         = "EC2"
  min_size                  = 0
  max_size                  = 1
  desired_capacity          = 0
  wait_for_capacity_timeout = 0

  tags = [
    {
      key                 = "Environment"
      value               = local.environment
      propagate_at_launch = true
    },
    {
      key                 = "Cluster"
      value               = local.name
      propagate_at_launch = true
    },
  ]
}

data "template_file" "user_data" {
  template = file("${path.module}/templates/user-data.sh")

  vars = {
    cluster_name = local.name
  }
}

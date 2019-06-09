/*
# ecs

A terraform module to create ecs resources
*/

locals {
  name        = "ecs"
  environment = "dev"

  # This is the convention we use to know what belongs to each other
  ec2_resources_name = "${local.name}-${local.environment}"
}

#----- ECS --------
module "ecs" {
  source = "terraform-aws-modules/ecs/aws"
  name   = local.name
}

/*
module "ec2-profile" {
  source = "terraform-aws-modules/ecs/aws/modules/ecs-instance-profile"
  name   = local.name
}
*/

#----- ECS  Services--------

/*
module "hello-world" {
  source     = "./service-hello-world"
  cluster_id = module.ecs.this_ecs_cluster_id
}
*/

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

resource "aws_security_group" "ecs_security_group" {
  vpc_id = module.vpc.vpc_id
}

/*
resource "aws_iam_instance_profile" "ecs_iam_instance_profile" {
  role = "ecs_iam_instance_profile"
}
*/

module "autoscaling" {
  source  = "terraform-aws-modules/autoscaling/aws"
  version = "~> 3.0"

  name = local.ec2_resources_name

  # Launch configuration
  lc_name = local.ec2_resources_name

  image_id             = data.aws_ami.amazon_linux_ecs.id
  instance_type        = "t2.micro"
  security_groups      = [aws_security_group.ecs_security_group.id]
  #iam_instance_profile = aws_iam_instance_profile.ecs_iam_instance_profile.id
  user_data            = data.template_file.user_data.rendered

  # Auto scaling group
  asg_name                  = local.ec2_resources_name
  vpc_zone_identifier       = module.vpc.public_subnets
  health_check_type         = "EC2"
  min_size                  = 1
  max_size                  = 1
  desired_capacity          = 1
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
  template = file("${path.module}/templates/userdata.sh")

  vars = {
    cluster_name = local.name
  }
}

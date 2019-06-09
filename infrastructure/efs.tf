//https://registry.terraform.io/modules/cloudposse/efs/aws/0.9.0
// network storage

module "efs" {
  source     = "git::https://github.com/cloudposse/terraform-aws-efs.git?ref=master"
  namespace  = "eg"
  stage      = "prod"
  name       = "app"
  attributes = ["efs"]

  aws_region         = "${var.aws_region}"
  vpc_id             = "${var.vpc_id}"
  subnets            = ["${var.private_subnets}"]
  availability_zones = ["${var.availability_zones}"]
  security_groups    = ["${var.security_group_id}"]

  zone_id = "${var.aws_route53_dns_zone_id}"
}

##############################################################
# Data sources to get VPC, subnets and security group details
##############################################################

locals {
  engine_name = "postgres"
  username = "username"
  password = "password"
}

resource "aws_security_group" "database_security_group"  {
  name = "ckan_db"
  vpc_id = module.vpc.vpc_id
}

resource "aws_db_option_group" "option_group" {
  engine_name = local.engine_name
  major_engine_version = "11"
}

resource "aws_db_parameter_group" "parameter_group" {
  family = "postgres11"
}

resource "aws_db_instance" "database" {
  allocated_storage = 20
  storage_type = "gp2"
  engine = local.engine_name
  engine_version = "11"
  instance_class = "db.t2.micro"
  name = "ckan_db"
  username = local.username
  password = local.password
  parameter_group_name = aws_db_parameter_group.parameter_group.name
  option_group_name = aws_db_option_group.option_group.name
  db_subnet_group_name = module.vpc.database_subnet_group
  vpc_security_group_ids = [aws_security_group.database_security_group.id]
  final_snapshot_identifier = "dbfinalsnapshot"
  skip_final_snapshot = true
}



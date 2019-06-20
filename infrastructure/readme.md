Instructions for setting up ckan infrastructure on AWS

These use terraform. Install terraform here: 
https://learn.hashicorp.com/terraform/getting-started/install.html

quick reference on mac with homebrew: 
`brew install terraform`

Terraform uses the AWS CLI, install that: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html

----


1. In console, move to `/infrastructure` directory
2. Copy the  `terraform.tfvars.example` to `terraform.tfvars` and fill out with your choices.
2. Run `terraform init` to initalize local terrform state
3. Run `terraform apply` to update your infrastructure.

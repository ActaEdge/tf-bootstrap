variable "region" {
  description = "AWS region"
  type        = string
}

variable "bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  type        = string
}

variable "dynamodb_table" {
  description = "Name of the DynamoDB table for state locking"
  type        = string
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "account_name" {
  description = "Name of the AWS account"
  type        = string
}
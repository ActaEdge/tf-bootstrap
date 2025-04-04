terraform {
  required_version = ">= 1.0.0"
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "example_bucket" {
  bucket = "${var.account_name}-example-bucket"

  tags = {
    Name        = "Example Bucket"
    Environment = "Development"
  }

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_public_access_block" "example_bucket_block" {
  bucket = aws_s3_bucket.example_bucket.id

  block_public_acls   = true
  block_public_policy = true
  ignore_public_acls  = true
  restrict_public_buckets = true
}
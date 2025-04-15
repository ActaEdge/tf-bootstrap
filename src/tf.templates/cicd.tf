locals {
  # Use empty string as fallback for GitHub variables to avoid errors
  github_org    = try(var.github_org, "")
  github_repo   = try(var.github_repo, "")
  github_branch = try(var.github_branch, "main")

  # Check if GitHub info is configured
  is_github_configured = local.github_org != "" && local.github_repo != ""
}

resource "aws_codebuild_project" "terraform_plan" {
  count         = local.is_github_configured ? 1 : 0
  name          = "tf-${var.account_name}-plan"
  description   = "CodeBuild project to run terraform plan"
  build_timeout = "10"
  service_role  = aws_iam_role.codebuild_role[0].arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:4.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
  }

  source {
    type            = "GITHUB"
    location        = "https://github.com/${local.github_org}/${local.github_repo}.git"
    git_clone_depth = 1
    buildspec       = "buildspec.yml"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebuild_logs[0].name
      stream_name = "build-log"
    }
  }

  tags = {
    Environment = "Terraform"
    Name        = "tf-${var.account_name}-cicd"
    AccountID   = var.account_id
  }
}

# Create CloudWatch log group explicitly
resource "aws_cloudwatch_log_group" "codebuild_logs" {
  count = local.is_github_configured ? 1 : 0
  name  = "codebuild-tf-${var.account_name}-plan-log-group"

  retention_in_days = 14

  tags = {
    Environment = "Terraform"
    Name        = "tf-${var.account_name}-cicd-logs"
  }
}

resource "aws_codepipeline" "terraform_pipeline" {
  count    = local.is_github_configured ? 1 : 0
  name     = "tf-${var.account_name}-pipeline"
  role_arn = aws_iam_role.codepipeline_role[0].arn

  artifact_store {
    location = aws_s3_bucket.terraform_state.id
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]

      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github[0].arn
        FullRepositoryId = "${local.github_org}/${local.github_repo}"
        BranchName       = local.github_branch
      }
    }
  }

  stage {
    name = "Plan"

    action {
      name            = "Plan"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      input_artifacts = ["source_output"]
      version         = "1"

      configuration = {
        ProjectName = aws_codebuild_project.terraform_plan[0].name
      }
    }
  }
}

resource "aws_codestarconnections_connection" "github" {
  count         = local.is_github_configured ? 1 : 0
  name          = "github-connection-${var.account_name}"
  provider_type = "GitHub"
}

resource "aws_iam_role" "codebuild_role" {
  count = local.is_github_configured ? 1 : 0
  name  = "codebuild-tf-${var.account_name}-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

# Attach AWS managed policy for CodeBuild to access CloudWatch Logs
resource "aws_iam_role_policy_attachment" "codebuild_logs_policy" {
  count      = local.is_github_configured ? 1 : 0
  role       = aws_iam_role.codebuild_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_iam_role_policy" "codebuild_policy" {
  count = local.is_github_configured ? 1 : 0
  role  = aws_iam_role.codebuild_role[0].name

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "${aws_s3_bucket.terraform_state.arn}",
        "${aws_s3_bucket.terraform_state.arn}/*"
      ],
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:GetBucketVersioning",
        "s3:PutObject"
      ]
    },
    {
      "Effect": "Allow",
      "Resource": [
        "${aws_dynamodb_table.terraform_locks.arn}"
      ],
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ]
    }
  ]
}
POLICY
}

resource "aws_iam_role" "codepipeline_role" {
  count = local.is_github_configured ? 1 : 0
  name  = "codepipeline-tf-${var.account_name}-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codepipeline.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "codepipeline_policy" {
  count = local.is_github_configured ? 1 : 0
  name  = "codepipeline_policy"
  role  = aws_iam_role.codepipeline_role[0].name

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect":"Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:GetBucketVersioning",
        "s3:PutObjectAcl",
        "s3:PutObject"
      ],
      "Resource": [
        "${aws_s3_bucket.terraform_state.arn}",
        "${aws_s3_bucket.terraform_state.arn}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "codestar-connections:UseConnection"
      ],
      "Resource": "${aws_codestarconnections_connection.github[0].arn}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "codebuild:BatchGetBuilds",
        "codebuild:StartBuild"
      ],
      "Resource": "${aws_codebuild_project.terraform_plan[0].arn}"
    }
  ]
}
EOF
}

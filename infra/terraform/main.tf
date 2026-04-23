# infra/terraform/main.tf
# Provisions all AWS resources for the Blind Navigation System
# Resources: IoT Core, Lambda, Rekognition IAM, S3, DynamoDB, CloudWatch

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "blind-navigation-system"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ──────────────────────────────────────────────
# IoT Core: Thing + Certificate + Policy
# ──────────────────────────────────────────────

resource "aws_iot_thing" "device" {
  name = "blindnav-${var.device_id}"
}

resource "aws_iot_certificate" "device_cert" {
  active = true
}

resource "aws_iot_policy" "device_policy" {
  name = "blindnav-device-policy-${var.environment}"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iot:Publish"]
        Resource = ["arn:aws:iot:${var.aws_region}:*:topic/blindnav/frames",
                    "arn:aws:iot:${var.aws_region}:*:topic/blindnav/health"]
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Subscribe", "iot:Receive"]
        Resource = ["arn:aws:iot:${var.aws_region}:*:topic/blindnav/results"]
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Connect"]
        Resource = ["arn:aws:iot:${var.aws_region}:*:client/blindnav-*"]
      }
    ]
  })
}

resource "aws_iot_policy_attachment" "device_cert_policy" {
  policy = aws_iot_policy.device_policy.name
  target = aws_iot_certificate.device_cert.arn
}

resource "aws_iot_thing_principal_attachment" "device_cert_attachment" {
  principal = aws_iot_certificate.device_cert.arn
  thing     = aws_iot_thing.device.name
}

# ──────────────────────────────────────────────
# S3: Frame archive bucket (7-day lifecycle)
# ──────────────────────────────────────────────

resource "aws_s3_bucket" "frames" {
  bucket = "blindnav-frames-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_lifecycle_configuration" "frames_lifecycle" {
  bucket = aws_s3_bucket.frames.id
  rule {
    id     = "expire-frames"
    status = "Enabled"
    expiration {
      days = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frames_encryption" {
  bucket = aws_s3_bucket.frames.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "frames_block_public" {
  bucket                  = aws_s3_bucket.frames.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ──────────────────────────────────────────────
# DynamoDB: Detection event log
# ──────────────────────────────────────────────

resource "aws_dynamodb_table" "detections" {
  name         = "blindnav-detections-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "device_id"
  range_key    = "timestamp"

  attribute {
    name = "device_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

# ──────────────────────────────────────────────
# IAM: Lambda execution role (least-privilege)
# ──────────────────────────────────────────────

resource "aws_iam_role" "lambda_role" {
  name = "blindnav-lambda-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "blindnav-lambda-policy"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["rekognition:DetectLabels"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem"]
        Resource = aws_dynamodb_table.detections.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.frames.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Publish"]
        Resource = "arn:aws:iot:${var.aws_region}:*:topic/blindnav/results"
      }
    ]
  })
}

# ──────────────────────────────────────────────
# CloudWatch: Alarm on high error rate
# ──────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "blindnav-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Lambda error rate too high for blind navigation system"
  dimensions = {
    FunctionName = "blindnav-processor-${var.environment}"
  }
}

data "aws_caller_identity" "current" {}

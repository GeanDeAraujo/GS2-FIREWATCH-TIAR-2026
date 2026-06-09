data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-lambda-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid    = "S3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.raw_images.arn,
      "${aws_s3_bucket.raw_images.arn}/*",
    ]
  }

  statement {
    sid    = "DynamoDBAccess"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:UpdateItem",
    ]
    resources = [
      aws_dynamodb_table.detections.arn,
      "${aws_dynamodb_table.detections.arn}/index/*",
    ]
  }

  statement {
    sid       = "SNSPublish"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }

  statement {
    sid    = "ECRAccess"
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name   = "${var.project_name}-lambda-policy-${var.environment}"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

# ── Processor Lambda (YOLO inference) — Docker image ───────────────────────────
resource "aws_lambda_function" "processor" {
  function_name = "${var.project_name}-processor-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = var.lambda_timeout_seconds
  memory_size   = var.lambda_memory_mb
  package_type  = "Image"

  # Built and pushed by lambda/build_and_push.sh
  image_uri = "${aws_ecr_repository.lambda_processor.repository_url}:latest"

  image_config {
    command = ["handler.lambda_handler"]
  }

  environment {
    variables = {
      DYNAMODB_TABLE_NAME       = aws_dynamodb_table.detections.name
      SNS_TOPIC_ARN             = aws_sns_topic.alerts.arn
      AWS_BUCKET_NAME           = aws_s3_bucket.raw_images.id
      YOLO_CONFIDENCE_THRESHOLD = var.yolo_confidence_threshold
      YOLO_MODEL_S3_KEY         = "models/firewatch_yolov8.pt"
      ENVIRONMENT               = var.environment
    }
  }

  depends_on = [aws_iam_role_policy.lambda_permissions]
}

# ── API Lambda (dashboard backend) — same Docker image, different handler ───────
resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-api-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 30
  memory_size   = 512
  package_type  = "Image"

  image_uri = "${aws_ecr_repository.lambda_processor.repository_url}:latest"

  image_config {
    command = ["api_handler.lambda_handler"]
  }

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.detections.name
      AWS_BUCKET_NAME     = aws_s3_bucket.raw_images.id
      ENVIRONMENT         = var.environment
    }
  }

  depends_on = [aws_iam_role_policy.lambda_permissions]
}

resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw_images.arn
}

resource "aws_cloudwatch_log_group" "lambda_processor_logs" {
  name              = "/aws/lambda/${aws_lambda_function.processor.function_name}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "lambda_api_logs" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 14
}

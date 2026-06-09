resource "aws_s3_bucket" "raw_images" {
  bucket = "${var.project_name}-raw-images-${var.environment}"
}

resource "aws_s3_bucket_versioning" "raw_images" {
  bucket = aws_s3_bucket.raw_images.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_images" {
  bucket = aws_s3_bucket.raw_images.id

  rule {
    id     = "expire-old-images"
    status = "Enabled"

    expiration {
      days = 90
    }

    filter {
      prefix = "raw/"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_images" {
  bucket = aws_s3_bucket.raw_images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw_images" {
  bucket                  = aws_s3_bucket.raw_images.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_notification" "trigger_lambda" {
  bucket = aws_s3_bucket.raw_images.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
  }

  depends_on = [aws_lambda_permission.s3_invoke]
}

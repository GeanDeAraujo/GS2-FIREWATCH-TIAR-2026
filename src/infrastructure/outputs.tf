output "s3_bucket_name" {
  description = "Name of the raw images S3 bucket"
  value       = aws_s3_bucket.raw_images.id
}

output "s3_bucket_arn" {
  description = "ARN of the raw images S3 bucket"
  value       = aws_s3_bucket.raw_images.arn
}

output "lambda_processor_name" {
  description = "Name of the YOLO processor Lambda function"
  value       = aws_lambda_function.processor.function_name
}

output "lambda_processor_arn" {
  description = "ARN of the YOLO processor Lambda function"
  value       = aws_lambda_function.processor.arn
}

output "lambda_api_name" {
  description = "Name of the API Lambda function"
  value       = aws_lambda_function.api.function_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for detections"
  value       = aws_dynamodb_table.detections.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.detections.arn
}

output "sns_topic_arn" {
  description = "ARN of the SNS alerts topic — set this as SNS_TOPIC_ARN in .env"
  value       = aws_sns_topic.alerts.arn
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge cron rule"
  value       = aws_cloudwatch_event_rule.processor_schedule.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL — used in build_and_push.sh"
  value       = aws_ecr_repository.lambda_processor.repository_url
}

output "api_gateway_url" {
  description = "API Gateway base URL — set as VITE_API_BASE_URL in src/dashboard/.env"
  value       = aws_api_gateway_stage.prod.invoke_url
}

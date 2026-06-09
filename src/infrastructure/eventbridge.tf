resource "aws_cloudwatch_event_rule" "processor_schedule" {
  name                = "${var.project_name}-schedule-${var.environment}"
  description         = "Triggers FireWatch processor Lambda every 15 minutes"
  schedule_expression = "rate(15 minutes)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "processor_lambda" {
  rule      = aws_cloudwatch_event_rule.processor_schedule.name
  target_id = "FireWatchProcessorLambda"
  arn       = aws_lambda_function.processor.arn
}

resource "aws_lambda_permission" "eventbridge_invoke" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.processor_schedule.arn
}

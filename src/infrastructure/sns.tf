resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts-${var.environment}"
}

# Corpo de Bombeiros — e-mail
resource "aws_sns_topic_subscription" "bombeiros_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Corpo de Bombeiros — SMS
resource "aws_sns_topic_subscription" "bombeiros_sms" {
  count     = var.alert_phone != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "sms"
  endpoint  = var.alert_phone
}

# IBAMA — Webhook (HTTP/HTTPS)
# Uncomment and set endpoint after configuring IBAMA integration
# resource "aws_sns_topic_subscription" "ibama_webhook" {
#   topic_arn = aws_sns_topic.alerts.arn
#   protocol  = "https"
#   endpoint  = var.ibama_webhook_url
# }

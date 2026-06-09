resource "aws_api_gateway_rest_api" "firewatch" {
  name        = "${var.project_name}-api-${var.environment}"
  description = "FireWatch REST API — detections, stats and alerts for the dashboard"
}

# ── /detections ────────────────────────────────────────────────────────────────
resource "aws_api_gateway_resource" "detections" {
  rest_api_id = aws_api_gateway_rest_api.firewatch.id
  parent_id   = aws_api_gateway_rest_api.firewatch.root_resource_id
  path_part   = "detections"
}

resource "aws_api_gateway_method" "detections_get" {
  rest_api_id   = aws_api_gateway_rest_api.firewatch.id
  resource_id   = aws_api_gateway_resource.detections.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "detections_get" {
  rest_api_id             = aws_api_gateway_rest_api.firewatch.id
  resource_id             = aws_api_gateway_resource.detections.id
  http_method             = aws_api_gateway_method.detections_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# ── /stats ─────────────────────────────────────────────────────────────────────
resource "aws_api_gateway_resource" "stats" {
  rest_api_id = aws_api_gateway_rest_api.firewatch.id
  parent_id   = aws_api_gateway_rest_api.firewatch.root_resource_id
  path_part   = "stats"
}

resource "aws_api_gateway_method" "stats_get" {
  rest_api_id   = aws_api_gateway_rest_api.firewatch.id
  resource_id   = aws_api_gateway_resource.stats.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "stats_get" {
  rest_api_id             = aws_api_gateway_rest_api.firewatch.id
  resource_id             = aws_api_gateway_resource.stats.id
  http_method             = aws_api_gateway_method.stats_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# ── /alerts ────────────────────────────────────────────────────────────────────
resource "aws_api_gateway_resource" "alerts" {
  rest_api_id = aws_api_gateway_rest_api.firewatch.id
  parent_id   = aws_api_gateway_rest_api.firewatch.root_resource_id
  path_part   = "alerts"
}

resource "aws_api_gateway_method" "alerts_get" {
  rest_api_id   = aws_api_gateway_rest_api.firewatch.id
  resource_id   = aws_api_gateway_resource.alerts.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "alerts_get" {
  rest_api_id             = aws_api_gateway_rest_api.firewatch.id
  resource_id             = aws_api_gateway_resource.alerts.id
  http_method             = aws_api_gateway_method.alerts_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# ── CORS (OPTIONS) ─────────────────────────────────────────────────────────────
locals {
  cors_resources = {
    detections = aws_api_gateway_resource.detections.id
    stats      = aws_api_gateway_resource.stats.id
    alerts     = aws_api_gateway_resource.alerts.id
  }
}

resource "aws_api_gateway_method" "cors" {
  for_each      = local.cors_resources
  rest_api_id   = aws_api_gateway_rest_api.firewatch.id
  resource_id   = each.value
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "cors" {
  for_each    = local.cors_resources
  rest_api_id = aws_api_gateway_rest_api.firewatch.id
  resource_id = each.value
  http_method = aws_api_gateway_method.cors[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "cors" {
  for_each    = local.cors_resources
  rest_api_id = aws_api_gateway_rest_api.firewatch.id
  resource_id = each.value
  http_method = aws_api_gateway_method.cors[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "cors" {
  for_each    = local.cors_resources
  rest_api_id = aws_api_gateway_rest_api.firewatch.id
  resource_id = each.value
  http_method = aws_api_gateway_method.cors[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.cors]
}

# ── Deployment ─────────────────────────────────────────────────────────────────
resource "aws_api_gateway_deployment" "prod" {
  rest_api_id = aws_api_gateway_rest_api.firewatch.id

  # Re-deploy whenever any route/method/integration changes; without this the
  # stage keeps serving the first deployment even after the API is edited.
  # Hasheamos os recursos INTEIROS (não só os .id): editar um atributo in-place
  # — ex.: o `uri` de uma integração, `request_templates` ou `authorization` —
  # altera o corpo e portanto o hash, forçando o redeploy. Os .id, por serem
  # derivados de rest_api_id/resource_id/http_method, não mudariam nesses casos.
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.detections,
      aws_api_gateway_resource.stats,
      aws_api_gateway_resource.alerts,
      aws_api_gateway_method.detections_get,
      aws_api_gateway_method.stats_get,
      aws_api_gateway_method.alerts_get,
      aws_api_gateway_integration.detections_get,
      aws_api_gateway_integration.stats_get,
      aws_api_gateway_integration.alerts_get,
      aws_api_gateway_integration.cors,
    ]))
  }

  depends_on = [
    aws_api_gateway_integration.detections_get,
    aws_api_gateway_integration.stats_get,
    aws_api_gateway_integration.alerts_get,
    aws_api_gateway_integration.cors,
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  rest_api_id   = aws_api_gateway_rest_api.firewatch.id
  deployment_id = aws_api_gateway_deployment.prod.id
  stage_name    = "prod"

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      integrationErr = "$context.integration.error"
    })
  }
}

resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = 14
}

# ── Lambda permission for API Gateway ──────────────────────────────────────────
resource "aws_lambda_permission" "api_gateway_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.firewatch.execution_arn}/*/*"
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "sa-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "firewatch"
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB (YOLO v8 requires at least 1024 MB)"
  type        = number
  default     = 2048
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "yolo_confidence_threshold" {
  description = "Minimum confidence score to trigger an alert (0.0 - 1.0)"
  type        = string
  default     = "0.75"
}

variable "alert_email" {
  description = "E-mail address for SNS alert subscription (Corpo de Bombeiros)"
  type        = string
  default     = ""
}

variable "alert_phone" {
  description = "Phone number for SNS SMS subscription in E.164 format e.g. +5511999999999"
  type        = string
  default     = ""
}

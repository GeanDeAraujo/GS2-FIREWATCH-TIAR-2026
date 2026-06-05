resource "aws_dynamodb_table" "detections" {
  name         = "${var.project_name}-detections-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "detection_id"
  range_key    = "timestamp"

  attribute {
    name = "detection_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "state"
    type = "S"
  }

  # GSI to query by Brazilian state (e.g. "SP", "AM")
  global_secondary_index {
    name            = "state-timestamp-index"
    hash_key        = "state"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

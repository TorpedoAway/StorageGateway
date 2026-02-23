# 1. Define the SNS Topic for Alerts
resource "aws_sns_topic" "gateway_health_alerts" {
  name = "storage-gateway-health-alerts"
}

# 2. Allow CloudWatch to publish to the SNS Topic
resource "aws_sns_topic_policy" "default" {
  arn = aws_sns_topic.gateway_health_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudWatchEvents"
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.gateway_health_alerts.arn
      }
    ]
  })
}

# 3. Create the CloudWatch Alarm
resource "aws_cloudwatch_metric_alarm" "sgw_health_alarm" {
  alarm_name          = "storage-gateway-health-notification"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "HealthNotifications"
  namespace           = "AWS/StorageGateway"
  period              = "300" # 5 minutes
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This alarm monitors Storage Gateway health notifications. If any notification occurs within 5 minutes, it triggers."
  
  # Replace with your actual Gateway ID or use a variable
  dimensions = {
    GatewayId = "sgw-12345678" 
  }

  alarm_actions = [aws_sns_topic.gateway_health_alerts.arn]
  ok_actions    = [aws_sns_topic.gateway_health_alerts.arn]
}

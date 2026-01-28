###############################################################
# SNS Topics for ML Pipeline Events                           #
###############################################################

###############################################################
# SNS Topic for ML Job Trigger Events                         #
###############################################################
resource "aws_sns_topic" "ml_trigger_events" {
  name = "${var.project_name}-ml-trigger-events"

  tags = var.common_tags
}

###############################################################
# SNS Topic for ML Job Notifications                          #
###############################################################
resource "aws_sns_topic" "ml_notifications" {
  name = "${var.project_name}-ml-notifications"

  tags = var.common_tags
}

###############################################################
# Email Subscriptions for Notifications (Optional)            #
###############################################################
resource "aws_sns_topic_subscription" "notification_emails" {
  count     = length(var.notification_emails)
  topic_arn = aws_sns_topic.ml_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_emails[count.index]
}

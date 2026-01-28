###############################################################
# S3 Bucket for ML Input (Scripts)                            #
###############################################################
resource "aws_s3_bucket" "ml_input_bucket" {
  bucket        = "${var.project_name}-ml-input"
  force_destroy = var.force_destroy

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-ml-input"
      Purpose = "ML Pipeline Input"
    }
  )
}

resource "aws_s3_bucket_versioning" "ml_input_versioning" {
  bucket = aws_s3_bucket.ml_input_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ml_input_encryption" {
  bucket = aws_s3_bucket.ml_input_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "ml_input_lifecycle" {
  bucket = aws_s3_bucket.ml_input_bucket.id

  rule {
    id     = "archive-old-inputs"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    expiration {
      days = var.input_retention_days
    }
  }
}

###############################################################
# S3 Bucket for ML Output (Results)                           #
###############################################################
resource "aws_s3_bucket" "ml_output_bucket" {
  bucket        = "${var.project_name}-ml-output"
  force_destroy = var.force_destroy

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-ml-output"
      Purpose = "ML Pipeline Output"
    }
  )
}

resource "aws_s3_bucket_versioning" "ml_output_versioning" {
  bucket = aws_s3_bucket.ml_output_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ml_output_encryption" {
  bucket = aws_s3_bucket.ml_output_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "ml_output_lifecycle" {
  bucket = aws_s3_bucket.ml_output_bucket.id

  rule {
    id     = "transition-old-results"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }
  }
}

###############################################################
# S3 Bucket for ML Models (Optional)                          #
###############################################################
resource "aws_s3_bucket" "ml_models_bucket" {
  count         = var.create_models_bucket ? 1 : 0
  bucket        = "${var.project_name}-ml-models"
  force_destroy = var.force_destroy

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-ml-models"
      Purpose = "ML Models Storage"
    }
  )
}

resource "aws_s3_bucket_versioning" "ml_models_versioning" {
  count  = var.create_models_bucket ? 1 : 0
  bucket = aws_s3_bucket.ml_models_bucket[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ml_models_encryption" {
  count  = var.create_models_bucket ? 1 : 0
  bucket = aws_s3_bucket.ml_models_bucket[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

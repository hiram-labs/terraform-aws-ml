###############################################################
# EFS for Persistent Model Storage                            #
# Allows models to be cached across batch jobs                #
###############################################################
resource "aws_efs_file_system" "model_cache" {
  creation_token = "${var.project_name}-model-cache"
  encrypted      = true

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-model-cache"
  })
}

resource "aws_efs_mount_target" "model_cache" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.model_cache.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs_sg.id]
}

resource "aws_efs_access_point" "model_cache" {
  file_system_id = aws_efs_file_system.model_cache.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-model-cache-access-point"
  })
}

resource "aws_security_group" "efs_sg" {
  name_prefix = "${var.project_name}-efs-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.common_tags
}

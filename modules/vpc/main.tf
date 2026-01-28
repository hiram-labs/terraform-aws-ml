###############################################################
# VPC Module for ML Pipeline                                  #
#                                                             #
# Creates VPC with public subnets configured for AWS Batch    #
# - Public subnets with auto-assign public IP                 #
# - Internet Gateway for external connectivity                #
# - Route tables for internet access                          #
###############################################################

###############################################################
# VPC                                                         #
###############################################################
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-vpc"
    }
  )
}

###############################################################
# Internet Gateway                                            #
###############################################################
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-igw"
    }
  )
}

###############################################################
# Public Subnets (Auto-assign Public IP Enabled)             #
###############################################################
resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true  # Critical for AWS Batch instances

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-public-subnet-${var.availability_zones[count.index]}"
      Type = "public"
    }
  )
}

###############################################################
# Route Table for Public Subnets                              #
###############################################################
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-public-rt"
    }
  )
}

resource "aws_route" "public_internet_gateway" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

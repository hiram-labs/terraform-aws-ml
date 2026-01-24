#!/bin/bash
###############################################################
# ECS GPU Instance User Data                                  #
# Configures ECS agent and NVIDIA drivers for GPU workloads   #
###############################################################

# Set ECS cluster name
echo ECS_CLUSTER=${cluster_name} >> /etc/ecs/ecs.config

# Enable GPU support in ECS
echo ECS_ENABLE_GPU_SUPPORT=true >> /etc/ecs/ecs.config

# Configure Docker runtime for NVIDIA
echo ECS_NVIDIA_RUNTIME=nvidia >> /etc/ecs/ecs.config

# Set container instance attributes
echo ECS_INSTANCE_ATTRIBUTES='{"gpu":"true"}' >> /etc/ecs/ecs.config

# Increase container stop timeout
echo ECS_CONTAINER_STOP_TIMEOUT=120s >> /etc/ecs/ecs.config

# Enable task IAM role
echo ECS_ENABLE_TASK_IAM_ROLE=true >> /etc/ecs/ecs.config
echo ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST=true >> /etc/ecs/ecs.config

# Restart ECS agent
systemctl restart ecs

# Verify NVIDIA driver installation
nvidia-smi

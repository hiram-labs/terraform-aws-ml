#!/bin/bash
###############################################################
# ECS Instance User Data                                      #
# Configures ECS agent and NVIDIA drivers for GPU instances   #
###############################################################

set -e

# Set ECS cluster name
echo ECS_CLUSTER=${cluster_name} >> /etc/ecs/ecs.config

# Enable GPU support (if available)
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU detected, enabling GPU support"
    echo ECS_ENABLE_GPU_SUPPORT=true >> /etc/ecs/ecs.config
    echo ECS_NVIDIA_RUNTIME=nvidia >> /etc/ecs/ecs.config
    echo ECS_INSTANCE_ATTRIBUTES='{"gpu":"true"}' >> /etc/ecs/ecs.config
fi

# Container configuration
echo ECS_CONTAINER_STOP_TIMEOUT=120s >> /etc/ecs/ecs.config

# Enable task IAM role
echo ECS_ENABLE_TASK_IAM_ROLE=true >> /etc/ecs/ecs.config
echo ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST=true >> /etc/ecs/ecs.config

# Restart ECS agent
systemctl restart ecs

# Verify setup
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Instance Setup Complete"
    nvidia-smi
else
    echo "Non-GPU Instance Setup Complete"
fi

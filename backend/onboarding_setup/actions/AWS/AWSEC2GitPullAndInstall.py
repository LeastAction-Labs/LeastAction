# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
codeblock = {
    "main.py":'''import boto3
import time
from botocore.exceptions import ClientError
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, git_repo_url, git_branch="main", repo_dir="/app/repo", **kwargs):
    """
    Pulls a private Git repository into an EC2 instance and installs dependencies.
    
    Parameters:
        least_action_action_object (dict): Action object containing connections and metadata
        git_repo_url (str): Full GitHub repository URL (e.g., https://github.com/org/repo)
        git_branch (str): Branch to pull (default: main)
        repo_dir (str): Directory on EC2 to clone into (default: /app/repo)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_info("action", "run", "start", "Starting EC2 Git pull and install action")
        
        git_connection = least_action_action_object.get('connection', {}).get('git_connection', {})
        ec2_connection = least_action_action_object.get('connection', {}).get('ec2_connection', {})
        
        git_username = git_connection.get('git_username')
        git_token = git_connection.get('git_token')
        ec2_instance_id = ec2_connection.get('ec2_instance_id')
        region = ec2_connection.get('region', 'us-east-1')
        aws_access_key_id = ec2_connection.get('aws_access_key_id')
        aws_secret_access_key = ec2_connection.get('aws_secret_access_key')

        if not git_username or not git_token:
            log_error("action", "run", "validate_git_credentials", "Git username or token missing")
            return False
        
        if not ec2_instance_id:
            log_error("action", "run", "validate_ec2_instance", "EC2 instance ID missing")
            return False
        
        if not git_repo_url:
            log_error("action", "run", "validate_git_repo", "Git repository URL missing")
            return False

        if not aws_access_key_id or not aws_secret_access_key:
            log_error("action", "run", "validate_aws_credentials", "AWS access key or secret key missing")
            return False
        
        log_info("action", "run", "validate_inputs", f"Validated inputs - Instance: {ec2_instance_id}, Region: {region}, Repo: {git_repo_url}, Branch: {git_branch}")
        
        ssm_client = boto3.client(
            'ssm',
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        
        log_info("action", "run", "initialize_ssm", "SSM client initialized successfully")
        
        git_url_with_auth = git_repo_url.replace(
            "https://",
            f"https://{git_username}:{git_token}@"
        )
        
        log_info("action", "run", "prepare_git_url", "Git URL prepared with authentication")
        
        check_dir_command = f"test -d {repo_dir} && echo 'EXISTS' || echo 'NOT_EXISTS'"
        
        log_info("action", "run", "check_repo_directory", f"Checking if directory exists: {repo_dir}")
        
        try:
            response = ssm_client.send_command(
                InstanceIds=[ec2_instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={"commands": [check_dir_command]},
                TimeoutSeconds=30
            )
            
            command_id = response['Command']['CommandId']
            log_info("action", "run", "check_repo_directory", f"Check directory command sent - CommandId: {command_id}")
            
            time.sleep(2)
            while True:
                output_response = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=ec2_instance_id
                )
                if output_response['Status'] not in ('Pending', 'InProgress'):
                    break
                time.sleep(2)
            
            dir_check_output = output_response.get('StandardOutputContent', '').strip()
            log_info("action", "run", "check_repo_directory", f"Directory check result: {dir_check_output}")
            
        except ClientError as e:
            log_error("action", "run", "check_repo_directory", f"Error checking directory: {str(e)}")
            return False
        
        if dir_check_output == "EXISTS":
            log_info("action", "run", "git_pull", f"Repository directory exists, pulling latest changes from {git_branch}")
            
            git_pull_command = f"cd {repo_dir} && git pull origin {git_branch}"
            
            try:
                response = ssm_client.send_command(
                    InstanceIds=[ec2_instance_id],
                    DocumentName="AWS-RunShellScript",
                    Parameters={"commands": [git_pull_command]},
                    TimeoutSeconds=60
                )
                
                command_id = response['Command']['CommandId']
                log_info("action", "run", "git_pull", f"Git pull command sent - CommandId: {command_id}")
                
                time.sleep(2)
                while True:
                    output_response = ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=ec2_instance_id
                    )
                    if output_response['Status'] not in ('Pending', 'InProgress'):
                        break
                    time.sleep(2)
                
                git_pull_output = output_response.get('StandardOutputContent', '')
                git_pull_error = output_response.get('StandardErrorContent', '')
                
                if output_response.get('Status') == 'Success':
                    log_info("action", "run", "git_pull", f"Git pull successful. Output: {git_pull_output}")
                else:
                    log_error("action", "run", "git_pull", f"Git pull failed. Error: {git_pull_error}")
                    return False
                    
            except ClientError as e:
                log_error("action", "run", "git_pull", f"Error executing git pull: {str(e)}")
                return False
        
        else:
            log_info("action", "run", "git_clone", f"Repository directory does not exist, cloning from {git_repo_url}")
            
            mkdir_command = f"mkdir -p {repo_dir}"
            
            try:
                response = ssm_client.send_command(
                    InstanceIds=[ec2_instance_id],
                    DocumentName="AWS-RunShellScript",
                    Parameters={"commands": [mkdir_command]},
                    TimeoutSeconds=30
                )
                
                command_id = response['Command']['CommandId']
                log_info("action", "run", "git_clone", f"Create directory command sent - CommandId: {command_id}")
                
                time.sleep(2)
                while True:
                    output_response = ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=ec2_instance_id
                    )
                    if output_response['Status'] not in ('Pending', 'InProgress'):
                        break
                    time.sleep(2)
                
                if output_response.get('Status') != 'Success':
                    log_error("action", "run", "git_clone", f"Failed to create directory: {output_response.get('StandardErrorContent', '')}")
                    return False
                
                log_info("action", "run", "git_clone", "Directory created successfully")
                
            except ClientError as e:
                log_error("action", "run", "git_clone", f"Error creating directory: {str(e)}")
                return False
            
            git_clone_command = f"cd {repo_dir} && git clone --branch {git_branch} {git_url_with_auth} ."
            
            try:
                response = ssm_client.send_command(
                    InstanceIds=[ec2_instance_id],
                    DocumentName="AWS-RunShellScript",
                    Parameters={"commands": [git_clone_command]},
                    TimeoutSeconds=120
                )
                
                command_id = response['Command']['CommandId']
                log_info("action", "run", "git_clone", f"Git clone command sent - CommandId: {command_id}")
                
                time.sleep(2)
                while True:
                    output_response = ssm_client.get_command_invocation(
                        CommandId=command_id,
                        InstanceId=ec2_instance_id
                    )
                    if output_response['Status'] not in ('Pending', 'InProgress'):
                        break
                    time.sleep(2)
                
                git_clone_output = output_response.get('StandardOutputContent', '')
                git_clone_error = output_response.get('StandardErrorContent', '')
                
                if output_response.get('Status') == 'Success':
                    log_info("action", "run", "git_clone", f"Git clone successful. Output: {git_clone_output}")
                else:
                    log_error("action", "run", "git_clone", f"Git clone failed. Error: {git_clone_error}")
                    return False
                    
            except ClientError as e:
                log_error("action", "run", "git_clone", f"Error executing git clone: {str(e)}")
                return False
        
        log_info("action", "run", "install_dependencies", "Starting dependency installation")
        
        pip_install_command = f"cd {repo_dir}/ticker_prediction && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 get-pip.py --break-system-packages && python3 -m pip install -r requirements.txt --break-system-packages --ignore-installed"
        try:
            response = ssm_client.send_command(
                InstanceIds=[ec2_instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={"commands": [pip_install_command]},
                TimeoutSeconds=300
            )
            
            command_id = response['Command']['CommandId']
            log_info("action", "run", "install_dependencies", f"Pip install command sent - CommandId: {command_id}")
            
            time.sleep(2)
            while True:
                output_response = ssm_client.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=ec2_instance_id
                )
                if output_response['Status'] not in ('Pending', 'InProgress'):
                    break
                time.sleep(2)
            
            pip_install_output = output_response.get('StandardOutputContent', '')
            pip_install_error = output_response.get('StandardErrorContent', '')
            
            if output_response.get('Status') == 'Success':
                log_info("action", "run", "install_dependencies", f"Pip install successful. Output: {pip_install_output}")
            else:
                log_error("action", "run", "install_dependencies", f"Pip install failed. Error: {pip_install_error}")
                return False
                
        except ClientError as e:
            log_error("action", "run", "install_dependencies", f"Error executing pip install: {str(e)}")
            return False
        
        log_info("action", "run", "complete", "EC2 Git pull and install action completed successfully")
        return True
        
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
    '''
}

bashblock = {
    "main.sh":'''#!/bin/bash
pip install boto3==1.34.84'''
}

action_variables={
  "git_repo_url": "https://github.com/org/repo",
  "git_branch": "main",
  "repo_dir": "/app/repo"
}
connection={
  "git_connection": {
    "git_username": "github_username",
    "git_token": "github_personal_access_token"
  },
  "ec2_connection": {
    "ec2_instance_id": "i-0123456789abcdef0",
    "region": "us-east-1"
  }
}

prompt = (
    "Pull a private Git repository onto an EC2 instance and install its dependencies via SSM Run Command. "
    "Action variables: git_repo_url, git_branch (default main), repo_dir (default /app/repo). "
    "Connection: git_connection (git_username + git_token) and ec2_connection (ec2_instance_id + region). "
    "Sends SSM commands to: 1) git clone/pull the repo using token auth, 2) run pip install -r requirements.txt. "
    "Returns True if all commands succeeded."
)

install_docs = """# EC2GitPullAndInstall — Install Guide

## Dependencies

    pip install boto3==1.34.84

## EC2 Instance Requirements

- SSM Agent installed and running
- AmazonSSMManagedInstanceCore policy attached to instance profile
- Git installed on the EC2 instance

## Connection

    {
      "git_connection": {
        "git_username": "github_username",
        "git_token": "ghp_xxxxxxxx"
      },
      "ec2_connection": {
        "ec2_instance_id": "i-0123456789abcdef0",
        "region": "us-east-1"
      }
    }
"""

guide_docs = """# EC2GitPullAndInstall — Action Guide

## What it does

Pulls a private Git repository onto an EC2 instance using SSM Run Command, then installs
Python dependencies. Useful for deploying code updates to EC2 instances as part of a
CI/CD or data pipeline workflow.

---

## Action Variables

    {
      "git_repo_url": "https://github.com/org/repo",
      "git_branch": "main",
      "repo_dir": "/app/repo"
    }

---

## Returns

True if the git pull and install succeeded. False on any error.
"""

description = """
Pulls a private Git repository onto an EC2 instance via SSM Run Command using token auth,
then installs Python dependencies. Combines git clone/pull with pip install as a deployment
action. Requires SSM Agent on the instance and a GitHub PAT in the connection.
"""

publisher = "LeastAction"

metadata = {
    "service": "EC2, SSM, GitHub",
    "category": "DevOps",
    "tags": ["ec2", "git", "deploy", "install", "ssm", "github", "aws"],
    "airflow_equivalent": "SSHOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

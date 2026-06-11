# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
codeblock = {
    "main.py":'''import requests
import json
from src.common.logger.logger import log_info, log_error


def run(least_action_action_object, webhook_url, message, channel=None, username=None, icon_emoji=None, icon_url=None, attachments=None, **kwargs):
    """
    Send a notification to Slack using a webhook URL.
    
    Parameters:
        least_action_action_object (dict): Action object containing metadata
        webhook_url (str): Slack webhook URL
        message (str): Message text to send
        channel (str): Optional channel name or ID to override webhook default
        username (str): Optional username to override webhook default
        icon_emoji (str): Optional emoji icon (e.g., :robot_face:)
        icon_url (str): Optional URL to custom icon image
        attachments (list): Optional list of attachment objects for rich formatting
    
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        log_info("action", "run", "start", "Starting Slack webhook notification")
        
        action_id = least_action_action_object.get('laui')
        session_id = least_action_action_object.get('session_id')
        log_info("action", "run", "initialize", "Action initialized")
        
        payload = {
            "text": message
        }
        
        if channel:
            payload["channel"] = channel
            log_info("action", "run", "configure_channel", f"Channel set to: {channel}")
        
        if username:
            payload["username"] = username
            log_info("action", "run", "configure_username", f"Username set to: {username}")
        
        if icon_emoji:
            payload["icon_emoji"] = icon_emoji
            log_info("action", "run", "configure_icon_emoji", f"Icon emoji set to: {icon_emoji}")
        
        if icon_url:
            payload["icon_url"] = icon_url
            log_info("action", "run", "configure_icon_url", f"Icon URL configured")
        
        if attachments:
            payload["attachments"] = attachments
            log_info("action", "run", "configure_attachments", f"Attachments added: {len(attachments)} attachment(s)")
        
        log_info("action", "run", "prepare_request", "Preparing HTTP request to Slack webhook")
        
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        log_info("action", "run", "send_request", f"HTTP request sent, Status Code: {response.status_code}")
        
        if response.status_code == 200:
            log_info("action", "run", "success", "Slack notification sent successfully")
            return True
        else:
            log_error("action", "run", "failed", f"Failed to send notification. Status: {response.status_code}, Response: {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        log_error("action", "run", "timeout", "Request timed out while sending Slack notification")
        return False
    except requests.exceptions.ConnectionError as e:
        log_error("action", "run", "connection_error", f"Connection error: {str(e)}")
        return False
    except requests.exceptions.RequestException as e:
        log_error("action", "run", "request_error", f"Request error: {str(e)}")
        return False
    except json.JSONDecodeError as e:
        log_error("action", "run", "json_error", f"JSON encoding error: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
    '''
}

bashblock = {
    "main.sh":'''pip install requests'''
}

action_variables={
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
  "message": "Task execution notification",
  "channel": "#general",
  "username": "LeastAction Bot",
  "icon_emoji": ":robot_face:",
  "icon_url": None,
  "attachments": None
}
connection={}

prompt = (
    "Send a webhook notification (e.g. Slack) with a custom message when a task event occurs. "
    "Action variables: webhook_url (required), message (required), channel (optional), "
    "username, icon_emoji, icon_url, attachments. "
    "POSTs a JSON payload to webhook_url. Returns True on success (HTTP 200). "
    "Use as a notification step after task completion, failure, or key milestones in a workflow."
)

install_docs = """# LeastActionWebhookNotify — Install Guide

## Dependencies

    pip install requests

## Slack Setup

1. Create an Incoming Webhook in your Slack workspace:
   https://api.slack.com/messaging/webhooks
2. Copy the webhook URL into the webhook_url action variable.
"""

guide_docs = """# LeastActionWebhookNotify — Action Guide

## What it does

Sends an HTTP POST to a webhook URL with a JSON message payload. Designed for Slack
Incoming Webhooks but works with any service that accepts POST with JSON body.

---

## Action Variables

    {
      "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx",
      "message": "Pipeline completed successfully",
      "channel": "#data-alerts",
      "username": "LeastAction Bot",
      "icon_emoji": ":white_check_mark:",
      "attachments": null
    }

---

## Returns

True if the webhook returned HTTP 200. False on any error.
"""

description = """
Sends a webhook notification (Slack-compatible) with a custom message. POSTs JSON to
webhook_url with message, channel, username, and icon fields. Returns True on HTTP 200.
"""

publisher = "LeastAction"

metadata = {
    "service": "Slack, Webhook",
    "category": "Notification",
    "tags": ["slack", "webhook", "notify", "alert", "message"],
    "airflow_equivalent": "SlackWebhookOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}

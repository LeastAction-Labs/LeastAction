# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
operator_type = "AWS"

codeblock = {'main.py': '''"""
AWS Resource Discovery & Cost Analysis Operator
- Full per-resource detail (EC2, RDS, S3, Lambda, DynamoDB, ELB) per region
- Empty regions and services skipped in output and Slack
- S3 storage sizes via ListObjectsV2 (FREE, instant)
- CloudWatch billing estimate (FREE, always runs)
- Linear month-end forecast (FREE, pure math — uses CE data when available)
- Cost Explorer behind enable_cost_explorer=true flag ($0.03/run when enabled)
- Auth: IAM role first; logs reason and falls back to explicit keys if role fails
"""

import boto3
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from src.common.logger.logger import log_info, log_error


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _get_tag(tags, key):
    for t in (tags or []):
        if t['Key'] == key:
            return t['Value']
    return None


def _check_iam_role(region='us-east-1'):
    """
    Probe whether an IAM role (instance profile / task role / assumed role)
    is available to this process. Returns (True, None) on success or
    (False, error_string) on failure.
    Uses sts:GetCallerIdentity — free, always available, forces eager
    credential resolution rather than waiting for the first real API call.
    """
    try:
        sts = boto3.client('sts', region_name=region)
        sts.get_caller_identity()
        return True, None
    except Exception as e:
        return False, str(e)


def _make_boto3_client(service, connection, region='us-east-1'):
    """
    Try IAM role first (instance profile / ECS task role / assumed role).
    If the role probe fails, log the reason and fall back to explicit keys
    from *connection* if present. Raises RuntimeError when neither works.
    """
    # --- attempt 1: IAM role ---
    role_ok, role_err = _check_iam_role(region)
    if role_ok:
        log_info("task", "initialize", "operation", "Operation")
        return boto3.client(service, region_name=region)

    log_error("task", "initialize", "operation", "Operation")

    # --- attempt 2: explicit key / secret ---
    if connection.get('aws_access_key_id') and connection.get('aws_secret_access_key'):
        kwargs = {
            'region_name':           region,
            'aws_access_key_id':     connection['aws_access_key_id'],
            'aws_secret_access_key': connection['aws_secret_access_key'],
        }
        if connection.get('aws_session_token'):
            kwargs['aws_session_token'] = connection['session_token']
        log_info("task", "initialize", f"explicit_keys_{service}_{region}",
                 "Using explicit access key credentials")
        return boto3.client(service, **kwargs)

    raise RuntimeError(
        f"No usable credentials for {service}/{region}: "
        "IAM role failed and no access keys are configured."
    )


def _build_regional_clients(service, regions, connection):
    """
    Build per-region clients for *service*.
    Performs a single IAM role probe (not one per region) and reuses the
    result for all regions. Falls back to explicit keys if the role fails.
    """
    clients = {}

    # One STS probe covers all regions — IAM role availability is process-wide.
    role_ok, role_err = _check_iam_role()
    if role_ok:
        log_info("task", "initialize", f"iam_role_check_{service}",
                 "IAM role verified — will use for all regions")
        key_kwargs = {}
    else:
        log_error("task", "initialize", f"iam_role_check_{service}",
                  f"IAM role check failed — reason: {role_err}. "
                  "Falling back to explicit keys per region.")
        if connection.get('aws_access_key_id') and connection.get('aws_secret_access_key'):
            key_kwargs = {
                'aws_access_key_id':     connection['aws_access_key_id'],
                'aws_secret_access_key': connection['aws_secret_access_key'],
            }
            if connection.get('aws_session_token'):
                key_kwargs['aws_session_token'] = connection['session_token']
        else:
            log_error("task", "initialize", f"no_credentials_{service}",
                      "IAM role failed and no explicit keys configured — "
                      "regional clients will be empty.")
            return {}

    for region in regions:
        try:
            clients[region] = boto3.client(service, region_name=region, **key_kwargs)
        except Exception as e:
            log_error("task", "initialize", f"regional_client_{service}_{region}", str(e))

    return clients


def _bytes_to_human(size_bytes):
    if size_bytes is None:
        return 'N/A'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def _strip_empty_regions(regional_dict):
    return {r: v for r, v in regional_dict.items() if v}


def _resolve_cost_window(payload_data):
    today = datetime.utcnow().date()

    if payload_data.get('cost_use_current_month', False):
        start = today.replace(day=1)
        end   = today
        log_info("task", "run", "cost_window_mode",
                 f"Using current-month window: {start} → {end}")
        return start, end

    if payload_data.get('cost_start_date'):
        try:
            start = datetime.strptime(payload_data['cost_start_date'], '%Y-%m-%d').date()
            end   = (
                datetime.strptime(payload_data['cost_end_date'], '%Y-%m-%d').date()
                if payload_data.get('cost_end_date') else today
            )
            if end > today:
                end = today
            log_info("task", "run", "cost_window_mode",
                     f"Using explicit date window: {start} → {end}")
            return start, end
        except ValueError as e:
            log_error("task", "run", "cost_window_date_parse",
                      f"Invalid date format — falling back to lookback. Error: {e}")

    lookback = int(payload_data.get('cost_lookback_days', 30))
    if lookback < 1:
        lookback = 30
    start = today - timedelta(days=lookback)
    end   = today
    log_info("task", "run", "cost_window_mode",
             f"Using lookback window: {lookback} days ({start} → {end})")
    return start, end


# ---------------------------------------------------------------------------
# FREE BILLING ESTIMATE — CloudWatch (no charge)
# ---------------------------------------------------------------------------

_CW_SERVICE_SHORT = {
    'Amazon Elastic Compute Cloud - Compute': 'EC2',
    'Amazon Relational Database Service':     'RDS',
    'Amazon Simple Storage Service':          'S3',
    'AWS Lambda':                             'Lambda',
    'Amazon DynamoDB':                        'DynamoDB',
    'Elastic Load Balancing':                 'ELB',
    'Amazon CloudWatch':                      'CloudWatch',
    'AWS Key Management Service':             'KMS',
    'Amazon Route 53':                        'Route53',
    'Amazon CloudFront':                      'CloudFront',
}


def _get_billing_estimate(cw_client):
    now   = datetime.utcnow()
    start = now - timedelta(days=1)

    result = {
        'total_estimated_usd': None,
        'by_service':          {},
        'source':              'CloudWatch/EstimatedCharges (free)',
        'as_of':               now.strftime('%Y-%m-%d %H:%M UTC'),
        'note':                'Updated by AWS every ~6 hours. Reflects MTD spend.',
    }

    try:
        resp = cw_client.get_metric_statistics(
            Namespace='AWS/Billing',
            MetricName='EstimatedCharges',
            Dimensions=[{'Name': 'Currency', 'Value': 'USD'}],
            StartTime=start,
            EndTime=now,
            Period=86400,
            Statistics=['Maximum'],
        )
        datapoints = resp.get('Datapoints', [])
        if datapoints:
            result['total_estimated_usd'] = round(
                max(d['Maximum'] for d in datapoints), 4
            )
        log_info("task", "run", "billing_estimate_total",
                 f"CW MTD estimate: ${result['total_estimated_usd']}")
    except Exception as e:
        log_error("task", "run", "billing_estimate_total", str(e))

    for svc, short in _CW_SERVICE_SHORT.items():
        try:
            resp = cw_client.get_metric_statistics(
                Namespace='AWS/Billing',
                MetricName='EstimatedCharges',
                Dimensions=[
                    {'Name': 'Currency',    'Value': 'USD'},
                    {'Name': 'ServiceName', 'Value': svc},
                ],
                StartTime=start,
                EndTime=now,
                Period=86400,
                Statistics=['Maximum'],
            )
            datapoints = resp.get('Datapoints', [])
            if datapoints:
                result['by_service'][short] = round(
                    max(d['Maximum'] for d in datapoints), 4
                )
        except Exception as e:
            log_error("task", "run", f"billing_estimate_{svc}", str(e))

    result['by_service'] = {
        k: v for k, v in result['by_service'].items() if v and v > 0
    }
    log_info("task", "run", "billing_estimate_services",
             f"Non-zero service estimates: {len(result['by_service'])}")
    return result


# ---------------------------------------------------------------------------
# FORECAST — linear projection using best available data source (free)
# ---------------------------------------------------------------------------

def _compute_linear_forecast(billing_estimate, ce_total=None, ce_by_service=None):
    """
    Project month-end spend using a linear daily-rate model.
    Prefers CE data when available (more accurate), falls back to
    CloudWatch estimate. Pure arithmetic — zero API cost.
    """
    today        = datetime.utcnow()
    day_of_month = today.day
    if today.month == 12:
        last_day = today.replace(day=31)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    days_in_month  = last_day.day
    days_remaining = days_in_month - day_of_month

    # Prefer CE total → fall back to CloudWatch estimate
    if ce_total is not None:
        total  = ce_total
        source = 'Cost Explorer'
        svc_map = ce_by_service or {}
    else:
        total  = billing_estimate.get('total_estimated_usd')
        source = 'CloudWatch Estimate'
        svc_map = billing_estimate.get('by_service', {})

    if total is None or day_of_month == 0:
        return {
            'projected_month_end_usd': None,
            'daily_rate_usd':          None,
            'days_elapsed':            day_of_month,
            'days_remaining':          days_remaining,
            'days_in_month':           days_in_month,
            'by_service':              {},
            'method':                  'linear_projection',
            'source':                  source,
            'note':                    'Insufficient billing data for projection.',
        }

    daily_rate = total / day_of_month
    projected  = round(total + daily_rate * days_remaining, 2)

    service_projections = {
        svc: round(amt + (amt / day_of_month) * days_remaining, 2)
        for svc, amt in svc_map.items()
        if amt and amt > 0
    }

    log_info("task", "run", "linear_forecast",
             f"Projected month-end: ${projected:.2f} "
             f"(${daily_rate:.2f}/day, day {day_of_month}/{days_in_month}) "
             f"[source: {source}]")

    return {
        'projected_month_end_usd': projected,
        'daily_rate_usd':          round(daily_rate, 4),
        'days_elapsed':            day_of_month,
        'days_remaining':          days_remaining,
        'days_in_month':           days_in_month,
        'by_service':              service_projections,
        'method':                  'linear_projection',
        'source':                  source,
        'note':                    (
            f"Based on ${total:.2f} MTD over {day_of_month} days "
            f"@ ${daily_rate:.2f}/day [{source}]"
        ),
    }


# ---------------------------------------------------------------------------
# COST EXPLORER — opt-in ($0.02 per run)
# ---------------------------------------------------------------------------

def _get_cost_data(ce_client, start_date, end_date):
    ce_end = end_date + timedelta(days=1)
    today  = datetime.utcnow().date()
    if ce_end > today + timedelta(days=1):
        ce_end = today

    cost_by_service = {}
    cost_by_region  = {}
    total = 0.0

    log_info("task", "run", "cost_explorer_query",
             f"CE query: {start_date} → {ce_end} [BILLED $0.02]")

    try:
        resp = ce_client.get_cost_and_usage(
            TimePeriod={'Start': str(start_date), 'End': str(ce_end)},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
        )
        for period in resp.get('ResultsByTime', []):
            for group in period.get('Groups', []):
                svc = group['Keys'][0]
                amt = float(group['Metrics']['UnblendedCost']['Amount'])
                if amt > 0:
                    cost_by_service[svc] = cost_by_service.get(svc, 0) + amt
                    total += amt
        log_info("task", "run", "cost_by_service",
                 f"CE total: ${total:.2f} across {len(cost_by_service)} services")
    except Exception as e:
        log_error("task", "run", "cost_by_service", str(e))

    try:
        resp = ce_client.get_cost_and_usage(
            TimePeriod={'Start': str(start_date), 'End': str(ce_end)},
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'REGION'}],
        )
        for period in resp.get('ResultsByTime', []):
            for group in period.get('Groups', []):
                reg = group['Keys'][0]
                amt = float(group['Metrics']['UnblendedCost']['Amount'])
                if amt > 0:
                    cost_by_region[reg] = cost_by_region.get(reg, 0) + amt
        log_info("task", "run", "cost_by_region",
                 f"CE region data: {len(cost_by_region)} active regions")
    except Exception as e:
        log_error("task", "run", "cost_by_region", str(e))

    return {
        'total_cost_usd': total,
        'by_service':     cost_by_service,
        'by_region':      cost_by_region,
        'window': {
            'start': str(start_date),
            'end':   str(end_date),
            'days':  (end_date - start_date).days,
        },
    }


def _get_ce_forecast(ce_client):
    today = datetime.utcnow().date()
    if today.month == 12:
        month_end = today.replace(day=31)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    forecast_start = today + timedelta(days=1)
    if forecast_start >= month_end:
        log_info("task", "run", "ce_forecast_skipped",
                 "No remaining days in month for CE forecast")
        return None

    try:
        resp  = ce_client.get_cost_forecast(
            TimePeriod={'Start': str(forecast_start), 'End': str(month_end)},
            Metric='UNBLENDED_COST',
            Granularity='MONTHLY',
        )
        total = float(resp['Total']['Amount'])
        fbt   = resp.get('ForecastResultsByTime', [{}])[0]
        lower = float(fbt.get('PredictionIntervalLowerBound', total))
        upper = float(fbt.get('PredictionIntervalUpperBound', total))
        log_info("task", "run", "ce_forecast",
                 f"CE remaining: ${total:.2f} (${lower:.2f}–${upper:.2f}) [BILLED $0.01]")
        return {
            'remaining_forecast_usd': round(total, 2),
            'lower_bound_usd':        round(lower, 2),
            'upper_bound_usd':        round(upper, 2),
            'forecast_until':         str(month_end),
            'source':                 'Cost Explorer Forecast API [billed $0.01]',
        }
    except Exception as e:
        log_error("task", "run", "ce_forecast", str(e))
        return None


# ---------------------------------------------------------------------------
# DISCOVERY
# ---------------------------------------------------------------------------

def _get_regions(ec2_client):
    try:
        resp = ec2_client.describe_regions()
        return [r['RegionName'] for r in resp['Regions']]
    except Exception as e:
        log_error("task", "run", "get_regions", str(e))
        return ['us-east-1']


def _discover_ec2(regional_clients):
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            resp = client.describe_instances()
            for r in resp['Reservations']:
                for inst in r['Instances']:
                    results[region].append({
                        'Name':         _get_tag(inst.get('Tags'), 'Name') or inst['InstanceId'],
                        'InstanceId':   inst['InstanceId'],
                        'InstanceType': inst['InstanceType'],
                        'State':        inst['State']['Name'],
                        'LaunchTime':   str(inst['LaunchTime']),
                        'PublicIP':     inst.get('PublicIpAddress', 'N/A'),
                        'PrivateIP':    inst.get('PrivateIpAddress', 'N/A'),
                        'VPC':          inst.get('VpcId', 'N/A'),
                        'KeyName':      inst.get('KeyName', 'N/A'),
                    })
            if results[region]:
                log_info("task", "run", f"ec2_{region}",
                         f"{len(results[region])} instances in {region}")
        except Exception as e:
            log_error("task", "run", f"ec2_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_rds(rds_client):
    results = defaultdict(list)
    try:
        resp = rds_client.describe_db_instances()
        for db in resp['DBInstances']:
            region = db['AvailabilityZone'][:-1]
            results[region].append({
                'Identifier': db['DBInstanceIdentifier'],
                'Engine':     f"{db['Engine']} {db['EngineVersion']}",
                'Class':      db['DBInstanceClass'],
                'Status':     db['DBInstanceStatus'],
                'Storage':    f"{db['AllocatedStorage']}GB",
                'MultiAZ':    db.get('MultiAZEnabled', False),
            })
        total = sum(len(v) for v in results.values())
        log_info("task", "run", "rds_discovery", f"{total} RDS instances found")
    except Exception as e:
        log_error("task", "run", "rds_discovery", str(e))
    return _strip_empty_regions(results)


def _get_s3_storage_sizes(s3_client, bucket_names):
    """
    Calculate S3 bucket sizes by summing object sizes via ListObjectsV2.
    FREE — no CloudWatch needed, instant, no delay.
    """
    sizes = {}
    for name in bucket_names:
        total_bytes  = 0
        object_count = 0
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=name):
                for obj in page.get('Contents', []):
                    total_bytes  += obj.get('Size', 0)
                    object_count += 1
            sizes[name] = {
                'bytes':        total_bytes if object_count > 0 else None,
                'object_count': object_count,
            }
            log_info("task", "run", f"s3_size_{name}",
                     f"{name}: {_bytes_to_human(total_bytes)} ({object_count} objects)")
        except Exception as e:
            log_error("task", "run", f"s3_size_{name}", str(e))
            sizes[name] = {'bytes': None, 'object_count': 0}
    return sizes


def _discover_s3(s3_client, cw_client):
    results = []
    try:
        buckets      = s3_client.list_buckets().get('Buckets', [])
        bucket_names = [b['Name'] for b in buckets]
        storage_map  = _get_s3_storage_sizes(s3_client, bucket_names)

        for b in buckets:
            name          = b['Name']
            region        = 'us-east-1'
            encryption    = 'Disabled'
            public_access = 'Unknown'

            try:
                loc    = s3_client.get_bucket_location(Bucket=name)
                region = loc['LocationConstraint'] or 'us-east-1'
            except Exception:
                pass
            try:
                s3_client.get_bucket_encryption(Bucket=name)
                encryption = 'Enabled'
            except Exception:
                pass
            try:
                pab = s3_client.get_public_access_block(
                    Bucket=name
                )['PublicAccessBlockConfiguration']
                public_access = 'Blocked' if all(pab.values()) else 'Open'
            except Exception:
                pass

            size_info    = storage_map.get(name, {'bytes': None, 'object_count': 0})
            size_bytes   = size_info['bytes']
            object_count = size_info['object_count']

            results.append({
                'BucketName':   name,
                'Region':       region,
                'CreationDate': str(b['CreationDate']),
                'Encryption':   encryption,
                'PublicAccess': public_access,
                'StorageBytes': size_bytes,
                'StorageHuman': _bytes_to_human(size_bytes),
                'ObjectCount':  object_count,
            })

        log_info("task", "run", "s3_discovery", f"{len(results)} S3 buckets found")
    except Exception as e:
        log_error("task", "run", "s3_discovery", str(e))
    return results


def _discover_lambda(regional_clients):
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            resp = client.list_functions()
            for fn in resp['Functions']:
                results[region].append({
                    'FunctionName':  fn['FunctionName'],
                    'Runtime':       fn.get('Runtime', 'N/A'),
                    'MemorySize':    fn.get('MemorySize'),
                    'Timeout':       fn.get('Timeout'),
                    'LastModified':  fn['LastModified'],
                    'CodeSizeBytes': fn.get('CodeSize'),
                    'CodeSizeHuman': _bytes_to_human(fn.get('CodeSize')),
                })
            if results[region]:
                log_info("task", "run", f"lambda_{region}",
                         f"{len(results[region])} functions in {region}")
        except Exception as e:
            log_error("task", "run", f"lambda_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_dynamodb(regional_clients):
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            tables = client.list_tables().get('TableNames', [])
            for tname in tables:
                try:
                    t = client.describe_table(TableName=tname)['Table']
                    results[region].append({
                        'TableName': tname,
                        'Status':    t['TableStatus'],
                        'ItemCount': t['ItemCount'],
                        'SizeBytes': t['TableSizeBytes'],
                        'SizeHuman': _bytes_to_human(t['TableSizeBytes']),
                    })
                except Exception as e:
                    log_error("task", "run", f"dynamodb_table_{tname}", str(e))
            if results[region]:
                log_info("task", "run", f"dynamodb_{region}",
                         f"{len(results[region])} tables in {region}")
        except Exception as e:
            log_error("task", "run", f"dynamodb_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_elbv2(regional_clients):
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            lbs = client.describe_load_balancers().get('LoadBalancers', [])
            for lb in lbs:
                results[region].append({
                    'Name':    lb['LoadBalancerName'],
                    'Type':    lb['Type'],
                    'Scheme':  lb['Scheme'],
                    'State':   lb['State']['Code'],
                    'DNSName': lb['DNSName'],
                })
            if results[region]:
                log_info("task", "run", f"elbv2_{region}",
                         f"{len(results[region])} load balancers in {region}")
        except Exception as e:
            log_error("task", "run", f"elbv2_{region}", str(e))
    return _strip_empty_regions(results)


# ---------------------------------------------------------------------------
# THRESHOLD EVALUATION
# ---------------------------------------------------------------------------

def _evaluate_thresholds(payload_data, cost_summary, billing_estimate,
                          resource_counts, s3_buckets, enable_cost_explorer):
    alerts = []
    limits = payload_data.get('warning_limits', {})

    def _add(severity, category, resource, threshold_label, actual_label, message):
        alerts.append({
            'severity':        severity,
            'category':        category,
            'resource':        resource,
            'threshold_label': threshold_label,
            'actual_label':    actual_label,
            'message':         message,
        })

    total = (
        cost_summary['total_cost_usd']
        if enable_cost_explorer and cost_summary
        else (billing_estimate.get('total_estimated_usd') or 0)
    )

    # 1. Total cost
    if limits.get('total_cost_critical_usd') and total >= limits['total_cost_critical_usd']:
        _add('CRITICAL', 'Total Cost', 'AWS Account',
             f"${limits['total_cost_critical_usd']:.2f}", f"${total:.2f}",
             "Spend has exceeded the critical threshold over the cost window.")
    elif limits.get('total_cost_warning_usd') and total >= limits['total_cost_warning_usd']:
        _add('WARNING', 'Total Cost', 'AWS Account',
             f"${limits['total_cost_warning_usd']:.2f}", f"${total:.2f}",
             "Spend has exceeded the warning threshold over the cost window.")

    # 2. Per-service cost (CE only)
    if enable_cost_explorer and cost_summary:
        for svc, svc_limits in limits.get('service_cost_limits', {}).items():
            actual = cost_summary['by_service'].get(svc, 0)
            if svc_limits.get('critical_usd') and actual >= svc_limits['critical_usd']:
                _add('CRITICAL', 'Service Cost', svc,
                     f"${svc_limits['critical_usd']:.2f}", f"${actual:.2f}",
                     f'{svc} cost has reached the critical level.')
            elif svc_limits.get('warning_usd') and actual >= svc_limits['warning_usd']:
                _add('WARNING', 'Service Cost', svc,
                     f"${svc_limits['warning_usd']:.2f}", f"${actual:.2f}",
                     f'{svc} cost has exceeded the warning level.')

        # 3. Per-region cost (CE only)
        for reg, reg_limits in limits.get('region_cost_limits', {}).items():
            actual = cost_summary['by_region'].get(reg, 0)
            if reg_limits.get('critical_usd') and actual >= reg_limits['critical_usd']:
                _add('CRITICAL', 'Region Cost', reg,
                     f"${reg_limits['critical_usd']:.2f}", f"${actual:.2f}",
                     f'Region {reg} cost has reached the critical level.')
            elif reg_limits.get('warning_usd') and actual >= reg_limits['warning_usd']:
                _add('WARNING', 'Region Cost', reg,
                     f"${reg_limits['warning_usd']:.2f}", f"${actual:.2f}",
                     f'Region {reg} cost has exceeded the warning level.')

    # 4. Resource count limits
    for svc, svc_limits in limits.get('resource_count_limits', {}).items():
        actual = resource_counts.get(svc, 0)
        if svc_limits.get('critical') and actual >= svc_limits['critical']:
            _add('CRITICAL', 'Resource Count', svc,
                 str(svc_limits['critical']), str(actual),
                 f'Number of {svc} resources has reached the critical threshold.')
        elif svc_limits.get('warning') and actual >= svc_limits['warning']:
            _add('WARNING', 'Resource Count', svc,
                 str(svc_limits['warning']), str(actual),
                 f'Number of {svc} resources has exceeded the warning threshold.')

    # 5. EC2 running instances
    running_ec2 = resource_counts.get('EC2_running', 0)
    if limits.get('ec2_running_critical') and running_ec2 >= limits['ec2_running_critical']:
        _add('CRITICAL', 'EC2 Running', 'EC2 Instances',
             str(limits['ec2_running_critical']), str(running_ec2),
             'Running EC2 instance count is critically high.')
    elif limits.get('ec2_running_warning') and running_ec2 >= limits['ec2_running_warning']:
        _add('WARNING', 'EC2 Running', 'EC2 Instances',
             str(limits['ec2_running_warning']), str(running_ec2),
             'Running EC2 instance count has exceeded the warning level.')

    # 6. S3 unencrypted buckets
    unencrypted = sum(1 for b in s3_buckets if b['Encryption'] == 'Disabled')
    if limits.get('s3_unencrypted_critical') is not None and unencrypted >= limits['s3_unencrypted_critical']:
        _add('CRITICAL', 'S3 Security', 'S3 Buckets',
             f"<{limits['s3_unencrypted_critical']} unencrypted",
             f"{unencrypted} unencrypted",
             'Multiple S3 buckets have no encryption enabled.')
    elif limits.get('s3_unencrypted_warning') is not None and unencrypted >= limits['s3_unencrypted_warning']:
        _add('WARNING', 'S3 Security', 'S3 Buckets',
             f"<{limits['s3_unencrypted_warning']} unencrypted",
             f"{unencrypted} unencrypted",
             'Some S3 buckets do not have encryption enabled.')

    # 7. S3 public buckets
    public_buckets = [b['BucketName'] for b in s3_buckets if b['PublicAccess'] == 'Open']
    if limits.get('s3_public_critical') is not None and len(public_buckets) >= limits['s3_public_critical']:
        _add('CRITICAL', 'S3 Security', ', '.join(public_buckets[:5]),
             f"<{limits['s3_public_critical']} public",
             f"{len(public_buckets)} public",
             'S3 buckets with public access detected. Immediate review required.')
    elif limits.get('s3_public_warning') is not None and len(public_buckets) >= limits['s3_public_warning']:
        _add('WARNING', 'S3 Security', ', '.join(public_buckets[:5]),
             f"<{limits['s3_public_warning']} public",
             f"{len(public_buckets)} public",
             'S3 buckets with public access detected.')

    # 8. Total S3 bucket count
    total_s3 = len(s3_buckets)
    if limits.get('s3_total_critical') and total_s3 >= limits['s3_total_critical']:
        _add('CRITICAL', 'S3 Bucket Count', 'S3',
             str(limits['s3_total_critical']), str(total_s3),
             'Total S3 bucket count is critically high.')
    elif limits.get('s3_total_warning') and total_s3 >= limits['s3_total_warning']:
        _add('WARNING', 'S3 Bucket Count', 'S3',
             str(limits['s3_total_warning']), str(total_s3),
             'Total S3 bucket count has exceeded the warning threshold.')

    log_info("task", "run", "threshold_evaluation",
             f"{len(alerts)} threshold violation(s) found")
    return alerts


# ---------------------------------------------------------------------------
# SLACK
# ---------------------------------------------------------------------------

def _send_slack_notification(webhook_url, blocks):
    payload = {'blocks': blocks}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        log_info("task", "run", "slack_notification_sent",
                 f"Slack responded {resp.status_code}")
    except Exception as e:
        log_error("task", "run", "slack_notification_failed", str(e))


def _safe_add_block(blocks, block):
    if len(blocks) < 49:
        blocks.append(block)
    elif len(blocks) == 49:
        blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': (
                    '_:warning: Message truncated at Slack block limit. '
                    'See JSON result for the full resource list._'
                )
            }
        })


def _build_slack_blocks(
    alerts, discovery_summary, cost_summary, billing_estimate, forecast,
    ec2_by_region, rds_by_region, s3_buckets,
    lambda_by_region, dynamo_by_region, elb_by_region,
    cost_window, enable_cost_explorer
):
    now         = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    has_crit    = any(a['severity'] == 'CRITICAL' for a in alerts)
    sev_icon    = ':red_circle:' if has_crit else ':large_yellow_circle:'
    alert_count = len(alerts)

    blocks = [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': f'{sev_icon}  AWS Cost & Resource Alert  {sev_icon}',
                'emoji': True,
            }
        },
        {
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': (
                    f'*LeastAction AWS Discovery* | {now} | '
                    f'*{alert_count} threshold(s) breached* | '
                    f'Window: *{cost_window["start"]}* → *{cost_window["end"]}* '
                    f'({cost_window["days"]} days)'
                )
            }]
        },
        {'type': 'divider'},
    ]

    # ── Cost snapshot ──────────────────────────────────────────────────────
    if enable_cost_explorer and cost_summary and cost_summary.get('total_cost_usd') is not None:
        total_cost   = cost_summary['total_cost_usd']
        top_services = sorted(
            ((s, v) for s, v in cost_summary.get('by_service', {}).items() if v > 0),
            key=lambda x: x[1], reverse=True
        )[:5]
        top_lines = '\\n'.join(
            f'• {s}: *${v:.2f}*' for s, v in top_services
        ) or '_No data_'
        _safe_add_block(blocks, {
            'type': 'section',
            'fields': [
                {
                    'type': 'mrkdwn',
                    'text': (
                        f'*:moneybag: Actual Cost (CE)*\\n*${total_cost:.2f}*\\n'
                        f'_{cost_window["start"]} → {cost_window["end"]}_'
                    )
                },
                {'type': 'mrkdwn', 'text': f'*:bar_chart: Top Services (CE)*\\n{top_lines}'},
            ]
        })
    else:
        total_est = billing_estimate.get('total_estimated_usd')
        est_str   = f'*${total_est:.2f}*' if total_est is not None else '_Unavailable_'
        svc_lines = '\\n'.join(
            f'• {s}: *${v:.2f}*'
            for s, v in sorted(
                billing_estimate.get('by_service', {}).items(),
                key=lambda x: x[1], reverse=True
            )[:5]
        ) or '_No data_'
        _safe_add_block(blocks, {
            'type': 'section',
            'fields': [
                {
                    'type': 'mrkdwn',
                    'text': (
                        f'*:moneybag: Est. MTD Charges (Free)*\\n{est_str}\\n'
                        f'_{billing_estimate.get("note", "")}_'
                    )
                },
                {'type': 'mrkdwn', 'text': f'*:bar_chart: Top Services (Est.)*\\n{svc_lines}'},
            ]
        })

    # ── Forecast section ───────────────────────────────────────────────────
    _safe_add_block(blocks, {'type': 'divider'})

    proj      = forecast.get('projected_month_end_usd')
    daily     = forecast.get('daily_rate_usd') or 0
    elapsed   = forecast.get('days_elapsed', 0)
    remaining = forecast.get('days_remaining', 0)
    total_d   = elapsed + remaining
    fc_source = forecast.get('source', 'Unknown')
    proj_text = f'*${proj:.2f}*' if proj is not None else '_Insufficient data_'

    ce_fc = forecast.get('ce_forecast')
    if ce_fc:
        proj_text += (
            f'\\nCE remaining: *${ce_fc["remaining_forecast_usd"]:.2f}*'
            f'\\nRange: ${ce_fc["lower_bound_usd"]:.2f} – ${ce_fc["upper_bound_usd"]:.2f}'
        )

    svc_proj_lines = '\\n'.join(
        f'• {s}: *${v:.2f}*'
        for s, v in sorted(
            forecast.get('by_service', {}).items(),
            key=lambda x: x[1], reverse=True
        )[:5]
    ) or '_No data_'

    _safe_add_block(blocks, {
        'type': 'section',
        'text': {'type': 'mrkdwn', 'text': f'*:crystal_ball: Forecast & Estimate* _(via {fc_source})_'}
    })
    _safe_add_block(blocks, {
        'type': 'section',
        'fields': [
            {
                'type': 'mrkdwn',
                'text': (
                    f'*Projected Month-End*\\n{proj_text}\\n'
                    f'_${daily:.2f}/day × {total_d} days_\\n'
                    f'_{forecast.get("note", "")}_'
                )
            },
            {
                'type': 'mrkdwn',
                'text': (
                    f'*:calendar: Month Progress*\\n'
                    f'Day *{elapsed}* of *{total_d}*\\n'
                    f'_{remaining} days remaining_\\n\\n'
                    f'*Top Service Projections*\\n{svc_proj_lines}'
                )
            },
        ]
    })

    # ── Resource summary ───────────────────────────────────────────────────
    _safe_add_block(blocks, {'type': 'divider'})
    res_lines = '\\n'.join(
        f'• {svc}: *{cnt}*'
        for svc, cnt in discovery_summary.get('resource_counts', {}).items()
        if cnt > 0
    ) or '_No active resources found_'

    _safe_add_block(blocks, {
        'type': 'section',
        'fields': [
            {
                'type': 'mrkdwn',
                'text': (
                    f'*:globe_with_meridians: Regions Scanned*\\n'
                    f'{discovery_summary.get("regions_scanned", 0)} total | '
                    f'{discovery_summary.get("regions_with_resources", 0)} with resources'
                )
            },
            {'type': 'mrkdwn', 'text': f'*:package: Active Resource Counts*\\n{res_lines}'},
        ]
    })

    # ── EC2 (skip if empty) ────────────────────────────────────────────────
    if ec2_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:computer: EC2 Instances*'}
        })
        for region, instances in sorted(ec2_by_region.items()):
            lines = '\\n'.join(
                f'  • *{i["Name"]}* | `{i["InstanceId"]}` | '
                f'`{i["InstanceType"]}` | _{i["State"]}_'
                for i in instances
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*{region}* ({len(instances)})\\n{lines}'
                }
            })

    # ── RDS (skip if empty) ────────────────────────────────────────────────
    if rds_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:floppy_disk: RDS Instances*'}
        })
        for region, dbs in sorted(rds_by_region.items()):
            lines = '\\n'.join(
                f'  • *{d["Identifier"]}* | {d["Engine"]} | '
                f'`{d["Class"]}` | {d["Storage"]} | _{d["Status"]}_'
                for d in dbs
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*{region}* ({len(dbs)})\\n{lines}'
                }
            })

    # ── S3 (skip if empty) ─────────────────────────────────────────────────
    if s3_buckets:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:bucket: S3 Buckets*'}
        })
        lines = '\\n'.join(
            f'  • *{b["BucketName"]}* | `{b["Region"]}` | '
            f'{b["StorageHuman"]} ({b["ObjectCount"]:,} objects) | '
            f'Enc: {b["Encryption"]} | Access: {b["PublicAccess"]}'
            for b in s3_buckets
        )
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f'*All Regions* ({len(s3_buckets)})\\n{lines}'
            }
        })

    # ── Lambda (skip if empty) ─────────────────────────────────────────────
    if lambda_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:zap: Lambda Functions*'}
        })
        for region, fns in sorted(lambda_by_region.items()):
            lines = '\\n'.join(
                f'  • *{f["FunctionName"]}* | {f["Runtime"]} | '
                f'{f["MemorySize"]}MB | {f["Timeout"]}s | {f["CodeSizeHuman"]}'
                for f in fns
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*{region}* ({len(fns)})\\n{lines}'
                }
            })

    # ── DynamoDB (skip if empty) ───────────────────────────────────────────
    if dynamo_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:card_index_dividers: DynamoDB Tables*'}
        })
        for region, tables in sorted(dynamo_by_region.items()):
            lines = '\\n'.join(
                f'  • *{t["TableName"]}* | {t["SizeHuman"]} | '
                f'{t["ItemCount"]:,} items | _{t["Status"]}_'
                for t in tables
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*{region}* ({len(tables)})\\n{lines}'
                }
            })

    # ── Load Balancers (skip if empty) ─────────────────────────────────────
    if elb_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:scales: Load Balancers*'}
        })
        for region, lbs in sorted(elb_by_region.items()):
            lines = '\\n'.join(
                f'  • *{lb["Name"]}* | {lb["Type"]} | {lb["Scheme"]} | _{lb["State"]}_'
                for lb in lbs
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*{region}* ({len(lbs)})\\n{lines}'
                }
            })

    # ── Alerts (skip if none) ──────────────────────────────────────────────
    if alerts:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f'*:rotating_light: Threshold Violations ({alert_count})*'
            }
        })
        for alert in alerts:
            icon = ':red_circle:' if alert['severity'] == 'CRITICAL' else ':large_yellow_circle:'
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (
                        f"{icon} *[{alert['severity']}] {alert['category']}*"
                        f" — {alert['resource']}\\n"
                        f">*Threshold:* {alert['threshold_label']}  |  "
                        f"*Actual:* {alert['actual_label']}\\n"
                        f">_{alert['message']}_"
                    )
                }
            })

    _safe_add_block(blocks, {'type': 'divider'})
    _safe_add_block(blocks, {
        'type': 'context',
        'elements': [{
            'type': 'mrkdwn',
            'text': (
                ':information_source: *LeastAction AWS Resource Discovery Operator* | '
                f'CE: {"enabled" if enable_cost_explorer else "disabled (free mode)"}'
            )
        }]
    })

    return blocks


# ---------------------------------------------------------------------------
# OPERATOR METHODS
# ---------------------------------------------------------------------------

def initialize(least_action_task_object):
    try:
        connection = least_action_task_object.get('connection', {})
        region     = connection.get('region', 'us-east-1')

        log_info("task", "initialize", "building_clients", "Building clients")

        ec2_base = _make_boto3_client('ec2', connection, region)
        regions  = _get_regions(ec2_base)

        log_info("task", "initialize", "regions_discovered", "Regions discovered")

        clients = {
            'ec2_base':        ec2_base,
            'rds':             _make_boto3_client('rds',        connection, region),
            's3':              _make_boto3_client('s3',         connection, region),
            'ce':              _make_boto3_client('ce',         connection, 'us-east-1'),
            'cw':              _make_boto3_client('cloudwatch', connection, 'us-east-1'),
            'ec2_regional':    _build_regional_clients('ec2',      regions, connection),
            'lambda_regional': _build_regional_clients('lambda',   regions, connection),
            'dynamo_regional': _build_regional_clients('dynamodb', regions, connection),
            'elbv2_regional':  _build_regional_clients('elbv2',    regions, connection),
            'regions':         regions,
        }

        log_info("task", "initialize", "clients_ready",
                 "All AWS clients initialised successfully")
        return clients

    except Exception as e:
        log_error("task", "initialize", "init_failed", str(e))
        raise


def run(least_action_task_object, client):
    try:
        connection           = least_action_task_object.get('connection', {})
        payload              = least_action_task_object.get('payload', {})
        payload_data         = payload.get('data', {})
        task_laui            = least_action_task_object.get('laui')
        slack_webhook        = connection.get('slack_webhook_url', '')
        enable_cost_explorer = bool(payload_data.get('enable_cost_explorer', False))

        log_info("task", "run", "start",
                 f"Starting AWS Resource Discovery | task: {task_laui} | "
                 f"CE: {'ENABLED ($0.03/run)' if enable_cost_explorer else 'DISABLED (free)'}")

        cost_start, cost_end = _resolve_cost_window(payload_data)

        log_info("task", "run", "discovering_ec2", "Fetching EC2 instances")
        ec2_by_region = _discover_ec2(client['ec2_regional'])

        log_info("task", "run", "discovering_rds", "Fetching RDS instances")
        rds_by_region = _discover_rds(client['rds'])

        log_info("task", "run", "discovering_s3",
                 "Fetching S3 buckets + storage sizes via ListObjectsV2 (free)")
        s3_buckets = _discover_s3(client['s3'], client['cw'])

        log_info("task", "run", "discovering_lambda", "Fetching Lambda functions")
        lambda_by_region = _discover_lambda(client['lambda_regional'])

        log_info("task", "run", "discovering_dynamodb", "Fetching DynamoDB tables")
        dynamo_by_region = _discover_dynamodb(client['dynamo_regional'])

        log_info("task", "run", "discovering_elbv2", "Fetching Load Balancers")
        elb_by_region = _discover_elbv2(client['elbv2_regional'])

        log_info("task", "run", "billing_estimate",
                 "Fetching CloudWatch billing estimate (free)")
        billing_estimate = _get_billing_estimate(client['cw'])

        # ── Cost Explorer + Forecast ───────────────────────────────────────
        cost_summary = None
        if enable_cost_explorer:
            log_info("task", "run", "fetching_costs",
                     f"CE query: {cost_start} → {cost_end} [BILLED $0.02]")
            cost_summary = _get_cost_data(client['ce'], cost_start, cost_end)

            forecast = _compute_linear_forecast(
                billing_estimate,
                ce_total      = cost_summary.get('total_cost_usd'),
                ce_by_service = cost_summary.get('by_service', {}),
            )

            log_info("task", "run", "fetching_ce_forecast",
                     "Fetching CE month-end forecast [BILLED $0.01]")
            ce_fc = _get_ce_forecast(client['ce'])
            if ce_fc:
                forecast['ce_forecast'] = ce_fc
        else:
            log_info("task", "run", "cost_explorer_skipped",
                     "CE disabled — free CW estimate in use. "
                     "Set enable_cost_explorer=true to enable.")
            cost_summary = {
                'total_cost_usd': None,
                'by_service':     {},
                'by_region':      {},
                'window': {
                    'start': str(cost_start),
                    'end':   str(cost_end),
                    'days':  (cost_end - cost_start).days,
                },
            }
            forecast = _compute_linear_forecast(billing_estimate)

        # ── Aggregate resource counts ──────────────────────────────────────
        all_ec2    = [i for lst in ec2_by_region.values()    for i in lst]
        all_rds    = [i for lst in rds_by_region.values()    for i in lst]
        all_lambda = [i for lst in lambda_by_region.values() for i in lst]
        all_dynamo = [i for lst in dynamo_by_region.values() for i in lst]
        all_elb    = [i for lst in elb_by_region.values()    for i in lst]

        resource_counts_raw = {
            'EC2':          len(all_ec2),
            'EC2_running':  sum(1 for i in all_ec2 if i['State'] == 'running'),
            'RDS':          len(all_rds),
            'S3':           len(s3_buckets),
            'Lambda':       len(all_lambda),
            'DynamoDB':     len(all_dynamo),
            'LoadBalancer': len(all_elb),
        }
        resource_counts = {k: v for k, v in resource_counts_raw.items() if v > 0}

        log_info("task", "run", "resource_counts",
                 f"Active resources: {json.dumps(resource_counts)}")

        discovery_summary = {
            'regions_scanned':        len(client['regions']),
            'regions_with_resources': len(set(
                list(ec2_by_region) + list(rds_by_region) +
                list(lambda_by_region) + list(dynamo_by_region) + list(elb_by_region)
            )),
            'resource_counts': resource_counts,
            'timestamp':       datetime.utcnow().isoformat(),
        }

        log_info("task", "run", "evaluating_thresholds",
                 "Comparing metrics against warning limits")
        alerts = _evaluate_thresholds(
            payload_data, cost_summary, billing_estimate,
            resource_counts_raw, s3_buckets, enable_cost_explorer
        )

        slack_sent = False
        if alerts and slack_webhook:
            log_info("task", "run", "sending_slack", "Sending slack")
            blocks = _build_slack_blocks(
                alerts, discovery_summary,
                cost_summary if enable_cost_explorer else None,
                billing_estimate, forecast,
                ec2_by_region, rds_by_region, s3_buckets,
                lambda_by_region, dynamo_by_region, elb_by_region,
                cost_summary['window'], enable_cost_explorer,
            )
            _send_slack_notification(slack_webhook, blocks)
            slack_sent = True
        elif alerts and not slack_webhook:
            log_error("task", "run", "slack_webhook_missing",
                      "Alerts found but no Slack webhook URL configured")
        else:
            log_info("task", "run", "no_alerts",
                     "No thresholds breached — Slack notification skipped")

        result = {
            'status':         'success',
            'execution_type': 'sync',
            'result': {
                'discovery_summary':    discovery_summary,
                'cost_summary':         cost_summary,
                'billing_estimate':     billing_estimate,
                'forecast':             forecast,
                'alerts':               alerts,
                'slack_sent':           slack_sent,
                'enable_cost_explorer': enable_cost_explorer,
                'resources': {
                    **(({'ec2':           ec2_by_region}    if ec2_by_region    else {})),
                    **(({'rds':           rds_by_region}    if rds_by_region    else {})),
                    **(({'s3':            s3_buckets}       if s3_buckets       else {})),
                    **(({'lambda':        lambda_by_region} if lambda_by_region else {})),
                    **(({'dynamodb':      dynamo_by_region} if dynamo_by_region else {})),
                    **(({'load_balancer': elb_by_region}    if elb_by_region    else {})),
                }
            }
        }

        log_info("task", "run", "complete",
                 f"Discovery complete — active: {list(result['result']['resources'].keys())} | "
                 f"alerts: {len(alerts)} | slack_sent: {slack_sent} | CE: {enable_cost_explorer}")
        return result

    except Exception as e:
        log_error("task", "run", "unexpected_error", str(e))
        return {
            'status':         'failed',
            'execution_type': 'sync',
            'result':         None,
            'error':          str(e)
        }


def check_completion(least_action_task_object, client, run_details):
    try:
        if run_details.get('execution_type') == 'sync':
            log_info("task", "check_completion", "sync_op",
                     "Synchronous operation — no polling required")
            return {
                'status':  run_details.get('status', 'success'),
                'message': 'AWS Resource Discovery completed synchronously',
                'output':  run_details.get('result')
            }
        if run_details.get('status') == 'failed':
            return {
                'status':  'failed',
                'message': run_details.get('error', 'Unknown error'),
                'output':  None
            }
        return {
            'status':  'success',
            'message': 'Completed',
            'output':  run_details.get('result')
        }
    except Exception as e:
        log_error("task", "check_completion", "unexpected_error", str(e))
        return {'status': 'failed', 'message': str(e), 'output': None}


def finish(least_action_task_object, client, completion_details, run_details):
    try:
        task_laui = least_action_task_object.get('laui')
        status    = completion_details.get('status', 'unknown')

        log_info("task", "finish", "final_status", "Final status")

        if status == 'success':
            output   = completion_details.get('output', {}) or {}
            summary  = output.get('discovery_summary', {})
            alerts   = output.get('alerts', [])
            window   = output.get('cost_summary', {}).get('window', {})
            forecast = output.get('forecast', {})
            log_info("task", "finish", "summary",
                     f"Regions scanned: {summary.get('regions_scanned')} | "
                     f"Regions with resources: {summary.get('regions_with_resources')} | "
                     f"Active services: {list(summary.get('resource_counts', {}).keys())} | "
                     f"Alerts: {len(alerts)} | "
                     f"Window: {window.get('start')} → {window.get('end')} | "
                     f"Forecast source: {forecast.get('source', 'N/A')} | "
                     f"Projected month-end: ${forecast.get('projected_month_end_usd', 'N/A')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get('message', 'No message'))

        log_info("task", "finish", "cleanup_complete", "Cleanup complete")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", str(e)) '''}

bashblock = {'main.sh': 
            '''#!/bin/bash
pip install boto3>=1.28.0
pip install botocore>=1.31.0
pip install tabulate>=0.9.0
pip install requests>=2.31.0

echo "Dependencies installed successfully"'''}

connection = {
  "region": "us-east-1",
  "slack_webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
}

payload = {
  "data": {
    "enable_cost_explorer": True,
    "cost_lookback_days": 30,
    "cost_start_date": "",
    "cost_end_date": "",
    "cost_use_current_month": False,
    "warning_limits": {
      "total_cost_warning_usd": 500,
      "total_cost_critical_usd": 1000,
      "service_cost_limits": {
        "Amazon EC2": {
          "warning_usd": 200,
          "critical_usd": 400
        },
        "Amazon RDS": {
          "warning_usd": 100,
          "critical_usd": 200
        },
        "AWS Lambda": {
          "warning_usd": 50,
          "critical_usd": 100
        },
        "Amazon S3": {
          "warning_usd": 30,
          "critical_usd": 60
        }
      },
      "region_cost_limits": {
        "us-east-1": {
          "warning_usd": 300,
          "critical_usd": 600
        },
        "eu-west-1": {
          "warning_usd": 150,
          "critical_usd": 300
        }
      },
      "resource_count_limits": {
        "EC2": {
          "warning": 20,
          "critical": 40
        },
        "RDS": {
          "warning": 10,
          "critical": 20
        },
        "Lambda": {
          "warning": 50,
          "critical": 100
        },
        "DynamoDB": {
          "warning": 20,
          "critical": 40
        },
        "LoadBalancer": {
          "warning": 10,
          "critical": 20
        },
        "S3": {
          "warning": 30,
          "critical": 60
        }
      },
      "ec2_running_warning": 10,
      "ec2_running_critical": 25,
      "s3_total_warning": 20,
      "s3_total_critical": 50,
      "s3_unencrypted_warning": 1,
      "s3_unencrypted_critical": 5,
      "s3_public_warning": 1,
      "s3_public_critical": 3
    }
  }
}
prompt = (
    "Discover all active AWS resources (EC2, RDS, S3, Lambda, DynamoDB, ELB) across all regions "
    "and report cost data with threshold alerting and Slack notifications. "
    "Always fetches a free CloudWatch billing estimate and computes a linear month-end cost forecast. "
    "Cost Explorer is opt-in via enable_cost_explorer=true (billed ~$0.03/run) for granular per-service "
    "and per-region breakdowns. S3 storage sizes are calculated via ListObjectsV2 (free, instant). "
    "Skips empty regions and services from output and Slack blocks. "
    "Evaluates configurable warning/critical thresholds for total cost, per-service cost, per-region cost, "
    "resource counts, running EC2 instances, and S3 encryption/public-access posture. "
    "Sends a structured Slack Block Kit message when thresholds are breached. "
    "Auth: IAM role via STS first, fallback to explicit access keys from connection."
)

install_docs = """# AWSResourceDiscoveryCostAnalysis — Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0
    pip install tabulate>=0.9.0
    pip install requests>=2.31.0

## AWS Permissions Required

    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeRegions",
        "ec2:DescribeInstances",
        "rds:DescribeDBInstances",
        "s3:ListAllMyBuckets",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:GetBucketEncryption",
        "s3:GetPublicAccessBlock",
        "lambda:ListFunctions",
        "dynamodb:ListTables",
        "dynamodb:DescribeTable",
        "elasticloadbalancing:DescribeLoadBalancers",
        "cloudwatch:GetMetricStatistics",
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2/ECS — no connection keys needed            |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add session_token in connection                    |

## Slack Setup

Provide a Slack Incoming Webhook URL in the connection field slack_webhook_url.
Notifications are only sent when at least one threshold is breached.
"""

guide_docs = """# AWSResourceDiscoveryCostAnalysis — Operator Guide

## What it does

Scans all AWS regions for active EC2, RDS, S3, Lambda, DynamoDB, and ELB resources.
Computes a free CloudWatch billing estimate and a linear month-end spend forecast.
Optionally queries Cost Explorer for exact per-service and per-region cost breakdowns.
Evaluates all findings against configurable warning/critical thresholds and sends a
structured Slack Block Kit notification when any threshold is breached.

Empty regions and services are always suppressed from output and Slack.

---

## Auth

1. IAM role — tried first via STS GetCallerIdentity. No keys needed in connection.
2. Access keys — fallback to aws_access_key_id + aws_secret_access_key from connection.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "",// optional — omit to use IAM role
      "aws_secret_access_key": "",// optional — omit to use IAM role
      "session_token": "",// optional — omit to use IAM role
      "slack_webhook_url": ""
    }

---

## Payload

    {
      "enable_cost_explorer": false,
      "cost_lookback_days": 30,
      "cost_start_date": "",
      "cost_end_date": "",
      "cost_use_current_month": false,
      "warning_limits": { ... }
    }

| Field                  | Required | Default | Description                                                        |
|------------------------|----------|---------|--------------------------------------------------------------------|
| enable_cost_explorer   | No       | false   | Enable Cost Explorer queries (~$0.03/run). Free CW estimate if off |
| cost_lookback_days     | No       | 30      | Days to look back for CE cost window                               |
| cost_start_date        | No       | —       | Explicit start date (YYYY-MM-DD). Overrides lookback               |
| cost_end_date          | No       | today   | Explicit end date (YYYY-MM-DD). Used with cost_start_date          |
| cost_use_current_month | No       | false   | Use calendar month-to-date window. Overrides all other date fields |
| warning_limits         | No       | {}      | Threshold config — see Threshold Reference below                   |

---

## Cost Window Priority

1. cost_use_current_month=true — month start to today
2. cost_start_date set — explicit range
3. fallback — today minus cost_lookback_days

---

## Threshold Reference (warning_limits)

    {
      "total_cost_warning_usd": 500,
      "total_cost_critical_usd": 1000,
      "service_cost_limits": {
        "Amazon EC2": { "warning_usd": 200, "critical_usd": 400 }
      },
      "region_cost_limits": {
        "us-east-1": { "warning_usd": 300, "critical_usd": 600 }
      },
      "resource_count_limits": {
        "EC2": { "warning": 20, "critical": 40 },
        "Lambda": { "warning": 50, "critical": 100 }
      },
      "ec2_running_warning": 10,
      "ec2_running_critical": 25,
      "s3_total_warning": 20,
      "s3_total_critical": 50,
      "s3_unencrypted_warning": 1,
      "s3_unencrypted_critical": 5,
      "s3_public_warning": 1,
      "s3_public_critical": 3
    }

service_cost_limits and region_cost_limits require enable_cost_explorer=true.

---

## Output (on success)

    {
      "discovery_summary": {
        "regions_scanned": 20,
        "regions_with_resources": 3,
        "resource_counts": { "EC2": 4, "S3": 12, "Lambda": 7 },
        "timestamp": "2026-04-12T10:00:00"
      },
      "cost_summary": { "total_cost_usd": 342.50, "by_service": {}, "by_region": {} },
      "billing_estimate": { "total_estimated_usd": 338.00, "by_service": {} },
      "forecast": { "projected_month_end_usd": 512.00, "daily_rate_usd": 17.12 },
      "alerts": [ { "severity": "WARNING", "category": "Total Cost" } ],
      "slack_sent": true,
      "resources": { "ec2": {}, "rds": {}, "s3": [], "lambda": {}, "dynamodb": {}, "load_balancer": {} }
    }

---

## Scenarios and Edge Cases

No thresholds configured:
  Discovery and cost data still run fully — Slack is simply not triggered.

enable_cost_explorer=false (default):
  CloudWatch EstimatedCharges is always fetched at no cost. Forecast uses CW data.
  service_cost_limits and region_cost_limits thresholds are skipped.

No Slack webhook configured:
  Alerts are still computed and returned in output — notification is skipped with a log warning.

IAM role unavailable and no keys provided:
  RuntimeError raised in initialize(). Task fails immediately with a clear message.

S3 buckets with many objects:
  ListObjectsV2 paginates fully per bucket. Large buckets will increase runtime proportionally.
"""

description = (
    "Discovers all active AWS resources (EC2, RDS, S3, Lambda, DynamoDB, ELB) across every region "
    "and produces a unified cost and inventory report. Always fetches a free CloudWatch MTD billing "
    "estimate and computes a linear month-end forecast. Cost Explorer is opt-in (enable_cost_explorer=true) "
    "for exact per-service and per-region breakdowns at ~$0.03/run. S3 storage sizes are computed via "
    "ListObjectsV2 at no charge. Evaluates configurable warning/critical thresholds across total cost, "
    "per-service cost, per-region cost, resource counts, running EC2 count, and S3 encryption and "
    "public-access posture. Sends a Slack Block Kit notification when thresholds are breached. "
    "Empty regions and services are suppressed from all output. "
    "Auth: IAM role via STS first, fallback to explicit access keys in connection."
)

publisher = "LeastActionLabs"

metadata = {
    "service": "EC2, RDS, S3, Lambda, DynamoDB, ELB, CloudWatch, Cost Explorer",
    "category": "FinOps",
    "tags": ["cost", "billing", "discovery", "ec2", "s3", "lambda", "rds", "dynamodb",
             "elb", "cloudwatch", "forecast", "slack", "alerts", "aws"],
    "airflow_equivalent": "BashOperator"
}

version_details = {"version": "0.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

Cost Explorer is opt-in via enable_cost_explorer=true — each run costs ~0.03 USD when enabled. The free CloudWatch billing estimate is always fetched and used for the linear forecast. S3 storage sizes are calculated via ListObjectsV2 (free). Slack is only sent when at least one threshold is breached. IAM role is tried first; falls back to explicit keys in connection. session_token key should be aws_session_token in the connection.
"""

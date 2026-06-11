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

codeblock = {'main.py': r'''"""
AWS Resource Discovery & Cost Analysis Operator
- Full per-resource detail per region for:
    EC2, RDS, S3, Lambda, DynamoDB, ALB/NLB/GLB (ELBv2),
    ECS (clusters + services + tasks), ECR (repositories + image counts),
    ElastiCache, CloudFront (CDN), NAT Gateways, VPCs, EKS,
    SQS, SNS, OpenSearch
- Discovery Health block in every Slack message:
    Every service listed with count found / empty / error status --
    so silent failures are immediately visible.
- Slack sent on EVERY run when a webhook is configured
    (not only on threshold breaches).
- Empty regions and services skipped in the detail sections
- S3 storage sizes via ListObjectsV2 (FREE, instant)
- CloudWatch billing estimate (FREE, always runs)
- Linear month-end forecast (FREE, pure math -- uses CE data when available)
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
    """
    try:
        sts = boto3.client('sts', region_name=region)
        sts.get_caller_identity()
        return True, None
    except Exception as e:
        return False, str(e)


def _make_boto3_client(service, connection, region='us-east-1'):
    """
    Try IAM role first. If the role probe fails, fall back to explicit keys
    from *connection* if present. Raises RuntimeError when neither works.
    """
    role_ok, role_err = _check_iam_role(region)
    if role_ok:
        log_info("task", "initialize", f"iam_role_ok_{service}_{region}",
                 "Using IAM role credentials")
        return boto3.client(service, region_name=region)

    log_error("task", "initialize", f"iam_role_failed_{service}_{region}",
              f"IAM role unavailable -- reason: {role_err}. Falling back to explicit keys.")

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
    Build per-region clients for *service* with a single IAM role probe.
    """
    clients = {}

    role_ok, role_err = _check_iam_role()
    if role_ok:
        log_info("task", "initialize", f"iam_role_check_{service}",
                 "IAM role verified -- will use for all regions")
        key_kwargs = {}
    else:
        log_error("task", "initialize", f"iam_role_check_{service}",
                  f"IAM role check failed -- reason: {role_err}. "
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
                      "IAM role failed and no explicit keys configured -- "
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
                 f"Using current-month window: {start} -> {end}")
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
                     f"Using explicit date window: {start} -> {end}")
            return start, end
        except ValueError as e:
            log_error("task", "run", "cost_window_date_parse",
                      f"Invalid date format -- falling back to lookback. Error: {e}")

    lookback = int(payload_data.get('cost_lookback_days', 30))
    if lookback < 1:
        lookback = 30
    start = today - timedelta(days=lookback)
    end   = today
    log_info("task", "run", "cost_window_mode",
             f"Using lookback window: {lookback} days ({start} -> {end})")
    return start, end


# ---------------------------------------------------------------------------
# FREE BILLING ESTIMATE -- CloudWatch (no charge)
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
    'Amazon ElastiCache':                     'ElastiCache',
    'Amazon Elastic Container Service':       'ECS',
    'Amazon Elastic Kubernetes Service':      'EKS',
    'Amazon Simple Queue Service':            'SQS',
    'Amazon Simple Notification Service':     'SNS',
    'Amazon OpenSearch Service':              'OpenSearch',
    'Amazon Virtual Private Cloud':           'VPC',
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
# FORECAST -- linear projection using best available data source (free)
# ---------------------------------------------------------------------------

def _compute_linear_forecast(billing_estimate, ce_total=None, ce_by_service=None):
    today        = datetime.utcnow()
    day_of_month = today.day
    if today.month == 12:
        last_day = today.replace(day=31)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    days_in_month  = last_day.day
    days_remaining = days_in_month - day_of_month

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
# COST EXPLORER -- opt-in ($0.03/run)
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
             f"CE query: {start_date} -> {ce_end} [BILLED $0.02]")

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
                 f"CE remaining: ${total:.2f} (${lower:.2f}-${upper:.2f}) [BILLED $0.01]")
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
# DISCOVERY -- original services
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
    """
    NOTE: Uses a single regional RDS client (base region).
    describe_db_instances returns all DB instances in that region only.
    RDS instances in other regions are not discovered from this call.
    To cover all regions, pass an rds_regional client map (same pattern
    as EC2/Lambda/ECS) and loop over regions -- left as the original
    behaviour intentionally to avoid multiplying describe_db_instances
    calls across all regions on every run.
    """
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
                    'ARN':     lb['LoadBalancerArn'],
                })
            if results[region]:
                log_info("task", "run", f"elbv2_{region}",
                         f"{len(results[region])} load balancers in {region}")
        except Exception as e:
            log_error("task", "run", f"elbv2_{region}", str(e))
    return _strip_empty_regions(results)


# ---------------------------------------------------------------------------
# DISCOVERY -- new services
# ---------------------------------------------------------------------------

def _discover_ecs(regional_clients):
    """
    Discover ECS clusters, services per cluster, and running task counts.
    Returns dict keyed by region, each value a list of cluster dicts.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            paginator     = client.get_paginator('list_clusters')
            cluster_arns  = []
            for page in paginator.paginate():
                cluster_arns.extend(page.get('clusterArns', []))

            if not cluster_arns:
                continue

            # Describe up to 100 clusters at a time (API limit)
            for i in range(0, len(cluster_arns), 100):
                batch = cluster_arns[i:i + 100]
                desc  = client.describe_clusters(
                    clusters=batch,
                    include=['TAGS', 'STATISTICS', 'SETTINGS'],
                )
                for c in desc.get('clusters', []):
                    cluster_name = c['clusterName']
                    services     = []

                    # List services for this cluster
                    try:
                        svc_paginator = client.get_paginator('list_services')
                        svc_arns      = []
                        for spage in svc_paginator.paginate(cluster=cluster_name):
                            svc_arns.extend(spage.get('serviceArns', []))

                        for j in range(0, len(svc_arns), 10):  # describe_services limit = 10
                            svc_batch = svc_arns[j:j + 10]
                            svc_desc  = client.describe_services(
                                cluster=cluster_name,
                                services=svc_batch,
                            )
                            for svc in svc_desc.get('services', []):
                                services.append({
                                    'ServiceName':    svc['serviceName'],
                                    'Status':         svc['status'],
                                    'DesiredCount':   svc['desiredCount'],
                                    'RunningCount':   svc['runningCount'],
                                    'PendingCount':   svc['pendingCount'],
                                    'LaunchType':     svc.get('launchType', 'N/A'),
                                    'TaskDefinition': svc['taskDefinition'].split('/')[-1],
                                })
                    except Exception as se:
                        log_error("task", "run", f"ecs_services_{cluster_name}", str(se))

                    results[region].append({
                        'ClusterName':         cluster_name,
                        'ClusterArn':          c['clusterArn'],
                        'Status':              c['status'],
                        'ActiveServicesCount': c.get('activeServicesCount', len(services)),
                        'RunningTasksCount':   c.get('runningTasksCount', 0),
                        'PendingTasksCount':   c.get('pendingTasksCount', 0),
                        'RegisteredContainerInstancesCount': c.get(
                            'registeredContainerInstancesCount', 0),
                        'Services': services,
                    })

            if results[region]:
                log_info("task", "run", f"ecs_{region}",
                         f"{len(results[region])} ECS clusters in {region}")
        except Exception as e:
            log_error("task", "run", f"ecs_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_elasticache(regional_clients):
    """
    Discover ElastiCache replication groups (Redis) and cache clusters (Memcached).
    Replication groups are the primary Redis construct; standalone clusters cover Memcached.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            # --- Redis: replication groups ---
            try:
                paginator = client.get_paginator('describe_replication_groups')
                for page in paginator.paginate():
                    for rg in page.get('ReplicationGroups', []):
                        # Collect node groups / shards
                        node_groups = rg.get('NodeGroups', [])
                        primary_ep  = 'N/A'
                        reader_ep   = 'N/A'
                        if rg.get('ConfigurationEndpoint'):
                            primary_ep = (
                                f"{rg['ConfigurationEndpoint']['Address']}:"
                                f"{rg['ConfigurationEndpoint']['Port']}"
                            )
                        elif node_groups:
                            ng = node_groups[0]
                            if ng.get('PrimaryEndpoint'):
                                primary_ep = (
                                    f"{ng['PrimaryEndpoint']['Address']}:"
                                    f"{ng['PrimaryEndpoint']['Port']}"
                                )
                            if ng.get('ReaderEndpoint'):
                                reader_ep = (
                                    f"{ng['ReaderEndpoint']['Address']}:"
                                    f"{ng['ReaderEndpoint']['Port']}"
                                )

                        results[region].append({
                            'Id':              rg['ReplicationGroupId'],
                            'Type':            'Redis',
                            'Status':          rg['Status'],
                            'Description':     rg.get('Description', ''),
                            'NumNodeGroups':   len(node_groups),
                            'NumReplicas':     rg.get('AutomaticFailover', 'disabled'),
                            'AtRestEncryption': rg.get('AtRestEncryptionEnabled', False),
                            'InTransitEncryption': rg.get('TransitEncryptionEnabled', False),
                            'MultiAZ':         rg.get('MultiAZ', 'disabled'),
                            'PrimaryEndpoint': primary_ep,
                            'ReaderEndpoint':  reader_ep,
                        })
            except Exception as re:
                log_error("task", "run", f"elasticache_redis_{region}", str(re))

            # --- Memcached: cache clusters (engine = memcached) ---
            try:
                paginator = client.get_paginator('describe_cache_clusters')
                for page in paginator.paginate(ShowCacheNodeInfo=True):
                    for cc in page.get('CacheClusters', []):
                        if cc.get('Engine', '').lower() != 'memcached':
                            continue  # Redis nodes are already covered via replication groups
                        ep = cc.get('ConfigurationEndpoint', {})
                        results[region].append({
                            'Id':     cc['CacheClusterId'],
                            'Type':   'Memcached',
                            'Status': cc['CacheClusterStatus'],
                            'NodeType':    cc.get('CacheNodeType', 'N/A'),
                            'NumNodes':    cc.get('NumCacheNodes', 0),
                            'EngineVersion': cc.get('EngineVersion', 'N/A'),
                            'Endpoint': (
                                f"{ep.get('Address', 'N/A')}:{ep.get('Port', 'N/A')}"
                                if ep else 'N/A'
                            ),
                        })
            except Exception as me:
                log_error("task", "run", f"elasticache_memcached_{region}", str(me))

            if results[region]:
                log_info("task", "run", f"elasticache_{region}",
                         f"{len(results[region])} ElastiCache clusters in {region}")
        except Exception as e:
            log_error("task", "run", f"elasticache_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_cloudfront(cf_client):
    """
    Discover CloudFront distributions (global service -- no region loop needed).
    Returns a flat list of distribution dicts.
    """
    results = []
    try:
        paginator = cf_client.get_paginator('list_distributions')
        for page in paginator.paginate():
            dist_list = page.get('DistributionList', {})
            for dist in dist_list.get('Items', []):
                # Origins summary
                origins = [
                    o.get('DomainName', 'N/A')
                    for o in dist.get('Origins', {}).get('Items', [])
                ]
                # Aliases (CNAMEs)
                aliases = dist.get('Aliases', {}).get('Items', [])

                results.append({
                    'Id':              dist['Id'],
                    'DomainName':      dist['DomainName'],
                    'Aliases':         aliases or ['(none)'],
                    'Status':          dist['Status'],
                    'Enabled':         dist.get('Enabled', True),
                    'PriceClass':      dist.get('PriceClass', 'N/A'),
                    'HttpsRequired':   dist.get('ViewerCertificate', {}).get(
                                           'MinimumProtocolVersion', 'N/A'),
                    'Origins':         origins,
                    'OriginCount':     len(origins),
                    'DefaultRootObject': dist.get('DefaultRootObject', ''),
                    'Comment':         dist.get('Comment', ''),
                    'LastModifiedTime': str(dist.get('LastModifiedTime', 'N/A')),
                })

        log_info("task", "run", "cloudfront_discovery",
                 f"{len(results)} CloudFront distributions found")
    except Exception as e:
        log_error("task", "run", "cloudfront_discovery", str(e))
    return results


def _discover_nat_gateways(regional_clients):
    """
    Discover NAT Gateways across all regions via the EC2 client.
    Returns dict keyed by region.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            paginator = client.get_paginator('describe_nat_gateways')
            for page in paginator.paginate():
                for ngw in page.get('NatGateways', []):
                    # Skip deleted gateways unless you want the history
                    if ngw['State'] == 'deleted':
                        continue

                    # Collect public + private IPs from NatGatewayAddresses
                    public_ips  = []
                    private_ips = []
                    for addr in ngw.get('NatGatewayAddresses', []):
                        if addr.get('PublicIp'):
                            public_ips.append(addr['PublicIp'])
                        if addr.get('PrivateIp'):
                            private_ips.append(addr['PrivateIp'])

                    results[region].append({
                        'NatGatewayId': ngw['NatGatewayId'],
                        'Name':         _get_tag(ngw.get('Tags'), 'Name') or ngw['NatGatewayId'],
                        'State':        ngw['State'],
                        'Type':         ngw.get('ConnectivityType', 'public'),
                        'VpcId':        ngw.get('VpcId', 'N/A'),
                        'SubnetId':     ngw.get('SubnetId', 'N/A'),
                        'PublicIPs':    public_ips,
                        'PrivateIPs':   private_ips,
                        'CreatedAt':    str(ngw.get('CreateTime', 'N/A')),
                    })

            if results[region]:
                log_info("task", "run", f"nat_{region}",
                         f"{len(results[region])} NAT Gateways in {region}")
        except Exception as e:
            log_error("task", "run", f"nat_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_vpcs(regional_clients):
    """
    Discover VPCs with their subnets and internet gateways.
    Returns dict keyed by region.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            vpcs = client.describe_vpcs().get('Vpcs', [])
            for vpc in vpcs:
                vpc_id   = vpc['VpcId']
                vpc_name = _get_tag(vpc.get('Tags'), 'Name') or vpc_id

                # Count subnets
                subnets = client.describe_subnets(
                    Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
                ).get('Subnets', [])
                public_subnets  = sum(1 for s in subnets if s.get('MapPublicIpOnLaunch'))
                private_subnets = len(subnets) - public_subnets

                # Internet gateways attached to this VPC
                igws = client.describe_internet_gateways(
                    Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
                ).get('InternetGateways', [])

                # Flow logs status
                fl_resp = client.describe_flow_logs(
                    Filters=[{'Name': 'resource-id', 'Values': [vpc_id]}]
                )
                flow_logs_enabled = bool(fl_resp.get('FlowLogs'))

                results[region].append({
                    'VpcId':          vpc_id,
                    'Name':           vpc_name,
                    'CidrBlock':      vpc.get('CidrBlock', 'N/A'),
                    'State':          vpc.get('State', 'N/A'),
                    'IsDefault':      vpc.get('IsDefault', False),
                    'TotalSubnets':   len(subnets),
                    'PublicSubnets':  public_subnets,
                    'PrivateSubnets': private_subnets,
                    'InternetGateways': [igw['InternetGatewayId'] for igw in igws],
                    'FlowLogsEnabled': flow_logs_enabled,
                })

            if results[region]:
                log_info("task", "run", f"vpc_{region}",
                         f"{len(results[region])} VPCs in {region}")
        except Exception as e:
            log_error("task", "run", f"vpc_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_eks(regional_clients):
    """
    Discover EKS clusters with their version, node groups, and status.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            paginator     = client.get_paginator('list_clusters')
            cluster_names = []
            for page in paginator.paginate():
                cluster_names.extend(page.get('clusters', []))

            for name in cluster_names:
                try:
                    desc    = client.describe_cluster(name=name)['cluster']
                    ng_resp = client.list_nodegroups(clusterName=name)
                    ng_names = ng_resp.get('nodegroups', [])

                    # Summarise node groups
                    node_groups = []
                    for ng_name in ng_names:
                        try:
                            ng = client.describe_nodegroup(
                                clusterName=name, nodegroupName=ng_name
                            )['nodegroup']
                            node_groups.append({
                                'Name':          ng_name,
                                'Status':        ng['status'],
                                'InstanceType':  ng.get('instanceTypes', ['N/A'])[0],
                                'DesiredSize':   ng.get('scalingConfig', {}).get('desiredSize'),
                                'MinSize':       ng.get('scalingConfig', {}).get('minSize'),
                                'MaxSize':       ng.get('scalingConfig', {}).get('maxSize'),
                                'AMIType':       ng.get('amiType', 'N/A'),
                                'CapacityType':  ng.get('capacityType', 'N/A'),
                            })
                        except Exception as nge:
                            log_error("task", "run", f"eks_ng_{name}_{ng_name}", str(nge))

                    results[region].append({
                        'ClusterName':     name,
                        'Version':         desc.get('version', 'N/A'),
                        'Status':          desc.get('status', 'N/A'),
                        'Endpoint':        desc.get('endpoint', 'N/A'),
                        'PlatformVersion': desc.get('platformVersion', 'N/A'),
                        'RoleArn':         desc.get('roleArn', 'N/A'),
                        'K8sNetworkCidr':  desc.get('kubernetesNetworkConfig', {}).get(
                                               'serviceIpv4Cidr', 'N/A'),
                        'LoggingEnabled':  any(
                            t.get('enabled', False)
                            for t in desc.get('logging', {}).get('clusterLogging', [])
                        ),
                        'NodeGroups':      node_groups,
                        'NodeGroupCount':  len(node_groups),
                    })
                except Exception as ce:
                    log_error("task", "run", f"eks_cluster_{name}_{region}", str(ce))

            if results[region]:
                log_info("task", "run", f"eks_{region}",
                         f"{len(results[region])} EKS clusters in {region}")
        except Exception as e:
            log_error("task", "run", f"eks_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_sqs(regional_clients):
    """
    Discover SQS queues with approximate message counts and queue attributes.
    """
    ATTRS = [
        'ApproximateNumberOfMessages',
        'ApproximateNumberOfMessagesNotVisible',
        'ApproximateNumberOfMessagesDelayed',
        'CreatedTimestamp',
        'LastModifiedTimestamp',
        'MessageRetentionPeriod',
        'VisibilityTimeout',
        'QueueArn',
    ]
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            paginator = client.get_paginator('list_queues')
            queue_urls = []
            for page in paginator.paginate():
                queue_urls.extend(page.get('QueueUrls', []))

            for url in queue_urls:
                queue_name = url.split('/')[-1]
                try:
                    attrs = client.get_queue_attributes(
                        QueueUrl=url, AttributeNames=ATTRS
                    ).get('Attributes', {})
                    results[region].append({
                        'QueueName':       queue_name,
                        'QueueUrl':        url,
                        'IsFifo':          queue_name.endswith('.fifo'),
                        'ApproxMessages':  int(attrs.get('ApproximateNumberOfMessages', 0)),
                        'InFlight':        int(attrs.get('ApproximateNumberOfMessagesNotVisible', 0)),
                        'Delayed':         int(attrs.get('ApproximateNumberOfMessagesDelayed', 0)),
                        'RetentionDays':   round(
                            int(attrs.get('MessageRetentionPeriod', 345600)) / 86400, 1),
                        'VisibilityTimeoutSec': int(attrs.get('VisibilityTimeout', 30)),
                    })
                except Exception as ae:
                    log_error("task", "run", f"sqs_attrs_{queue_name}", str(ae))

            if results[region]:
                log_info("task", "run", f"sqs_{region}",
                         f"{len(results[region])} SQS queues in {region}")
        except Exception as e:
            log_error("task", "run", f"sqs_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_sns(regional_clients):
    """
    Discover SNS topics with subscription counts and delivery policy metadata.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            paginator   = client.get_paginator('list_topics')
            topic_arns  = []
            for page in paginator.paginate():
                topic_arns.extend([t['TopicArn'] for t in page.get('Topics', [])])

            for arn in topic_arns:
                topic_name = arn.split(':')[-1]
                try:
                    attrs = client.get_topic_attributes(TopicArn=arn).get('Attributes', {})
                    results[region].append({
                        'TopicName':              topic_name,
                        'TopicArn':               arn,
                        'SubscriptionsConfirmed': int(attrs.get('SubscriptionsConfirmed', 0)),
                        'SubscriptionsPending':   int(attrs.get('SubscriptionsPending', 0)),
                        'SubscriptionsDeleted':   int(attrs.get('SubscriptionsDeleted', 0)),
                        'ContentBasedDeduplication': attrs.get(
                            'ContentBasedDeduplication', 'false') == 'true',
                        'FifoTopic':              attrs.get('FifoTopic', 'false') == 'true',
                        'KmsMasterKeyId':         attrs.get('KmsMasterKeyId', 'N/A'),
                    })
                except Exception as ae:
                    log_error("task", "run", f"sns_attrs_{topic_name}", str(ae))

            if results[region]:
                log_info("task", "run", f"sns_{region}",
                         f"{len(results[region])} SNS topics in {region}")
        except Exception as e:
            log_error("task", "run", f"sns_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_opensearch(regional_clients):
    """
    Discover Amazon OpenSearch Service domains with cluster config and encryption status.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            domain_names = [
                d['DomainName']
                for d in client.list_domain_names().get('DomainNames', [])
            ]
            if not domain_names:
                continue

            # describe up to 5 at a time (API limit)
            for i in range(0, len(domain_names), 5):
                batch = domain_names[i:i + 5]
                descs = client.describe_domains(DomainNames=batch).get('DomainStatusList', [])
                for d in descs:
                    cluster_cfg = d.get('ClusterConfig', {})
                    ep_map      = d.get('Endpoints', {})
                    endpoint    = (
                        d.get('Endpoint')
                        or ep_map.get('vpc')
                        or ep_map.get('dashboard')
                        or 'N/A'
                    )
                    results[region].append({
                        'DomainName':       d['DomainName'],
                        'ARN':              d.get('ARN', 'N/A'),
                        'EngineVersion':    d.get('EngineVersion', 'N/A'),
                        'Status':           'Active' if d.get('Created') else 'Creating',
                        'Processing':       d.get('Processing', False),
                        'Endpoint':         endpoint,
                        'InstanceType':     cluster_cfg.get('InstanceType', 'N/A'),
                        'InstanceCount':    cluster_cfg.get('InstanceCount', 0),
                        'DedicatedMaster':  cluster_cfg.get('DedicatedMasterEnabled', False),
                        'MasterType':       cluster_cfg.get('DedicatedMasterType', 'N/A'),
                        'MasterCount':      cluster_cfg.get('DedicatedMasterCount', 0),
                        'ZoneAwareness':    cluster_cfg.get('ZoneAwarenessEnabled', False),
                        'StorageType':      d.get('EBSOptions', {}).get('EBSEnabled', False),
                        'VolumeGB':         d.get('EBSOptions', {}).get('VolumeSize', 0),
                        'EncryptionAtRest': d.get('EncryptionAtRestOptions', {}).get(
                                                'Enabled', False),
                        'NodeToNodeEncryption': d.get('NodeToNodeEncryptionOptions', {}).get(
                                                    'Enabled', False),
                    })

            if results[region]:
                log_info("task", "run", f"opensearch_{region}",
                         f"{len(results[region])} OpenSearch domains in {region}")
        except Exception as e:
            log_error("task", "run", f"opensearch_{region}", str(e))
    return _strip_empty_regions(results)


def _discover_ecr(regional_clients):
    """
    Discover ECR private repositories with image count, size, scan config,
    and tag mutability. Lifecycle policy and encryption status are included.
    Only private registries are covered -- public ECR (gallery.ecr.aws) is
    a separate endpoint and is not discovered here.
    """
    results = defaultdict(list)
    for region, client in regional_clients.items():
        try:
            paginator = client.get_paginator('describe_repositories')
            for page in paginator.paginate():
                for repo in page.get('repositories', []):
                    repo_name = repo['repositoryName']
                    image_count  = 0
                    total_bytes  = 0
                    latest_pushed = 'N/A'

                    # Count images and sum their sizes
                    try:
                        img_paginator = client.get_paginator('describe_images')
                        for img_page in img_paginator.paginate(repositoryName=repo_name):
                            for img in img_page.get('imageDetails', []):
                                image_count += 1
                                total_bytes += img.get('imageSizeInBytes', 0)
                                pushed = img.get('imagePushedAt')
                                if pushed:
                                    pushed_str = str(pushed)
                                    if latest_pushed == 'N/A' or pushed_str > latest_pushed:
                                        latest_pushed = pushed_str
                    except Exception as ie:
                        log_error("task", "run", f"ecr_images_{repo_name}", str(ie))

                    # Lifecycle policy existence check
                    has_lifecycle = False
                    try:
                        client.get_lifecycle_policy(repositoryName=repo_name)
                        has_lifecycle = True
                    except client.exceptions.LifecyclePolicyNotFoundException:
                        pass
                    except Exception:
                        pass

                    results[region].append({
                        'RepositoryName':  repo_name,
                        'RepositoryUri':   repo.get('repositoryUri', 'N/A'),
                        'CreatedAt':       str(repo.get('createdAt', 'N/A')),
                        'ImageCount':      image_count,
                        'TotalSizeBytes':  total_bytes,
                        'TotalSizeHuman':  _bytes_to_human(total_bytes) if image_count > 0 else 'N/A',
                        'LatestPush':      latest_pushed,
                        'TagMutability':   repo.get('imageTagMutability', 'N/A'),
                        'ScanOnPush':      repo.get('imageScanningConfiguration', {}).get(
                                               'scanOnPush', False),
                        'EncryptionType':  repo.get('encryptionConfiguration', {}).get(
                                               'encryptionType', 'AES256'),
                        'HasLifecyclePolicy': has_lifecycle,
                    })

            if results[region]:
                log_info("task", "run", f"ecr_{region}",
                         f"{len(results[region])} ECR repositories in {region}")
        except Exception as e:
            log_error("task", "run", f"ecr_{region}", str(e))
    return _strip_empty_regions(results)

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
    if (limits.get('s3_unencrypted_critical') is not None
            and unencrypted >= limits['s3_unencrypted_critical']):
        _add('CRITICAL', 'S3 Security', 'S3 Buckets',
             f"<{limits['s3_unencrypted_critical']} unencrypted",
             f"{unencrypted} unencrypted",
             'Multiple S3 buckets have no encryption enabled.')
    elif (limits.get('s3_unencrypted_warning') is not None
          and unencrypted >= limits['s3_unencrypted_warning']):
        _add('WARNING', 'S3 Security', 'S3 Buckets',
             f"<{limits['s3_unencrypted_warning']} unencrypted",
             f"{unencrypted} unencrypted",
             'Some S3 buckets do not have encryption enabled.')

    # 7. S3 public buckets
    public_buckets = [b['BucketName'] for b in s3_buckets if b['PublicAccess'] == 'Open']
    if (limits.get('s3_public_critical') is not None
            and len(public_buckets) >= limits['s3_public_critical']):
        _add('CRITICAL', 'S3 Security', ', '.join(public_buckets[:5]),
             f"<{limits['s3_public_critical']} public",
             f"{len(public_buckets)} public",
             'S3 buckets with public access detected. Immediate review required.')
    elif (limits.get('s3_public_warning') is not None
          and len(public_buckets) >= limits['s3_public_warning']):
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

    # 9. ECS running tasks
    running_tasks = resource_counts.get('ECS_tasks_running', 0)
    if limits.get('ecs_tasks_critical') and running_tasks >= limits['ecs_tasks_critical']:
        _add('CRITICAL', 'ECS Running Tasks', 'ECS',
             str(limits['ecs_tasks_critical']), str(running_tasks),
             'Running ECS task count has reached the critical threshold.')
    elif limits.get('ecs_tasks_warning') and running_tasks >= limits['ecs_tasks_warning']:
        _add('WARNING', 'ECS Running Tasks', 'ECS',
             str(limits['ecs_tasks_warning']), str(running_tasks),
             'Running ECS task count has exceeded the warning threshold.')

    # 10. VPCs without flow logs
    vpc_no_fl = resource_counts.get('VPC_no_flow_logs', 0)
    if limits.get('vpc_no_flow_logs_critical') and vpc_no_fl >= limits['vpc_no_flow_logs_critical']:
        _add('CRITICAL', 'VPC Security', 'VPCs',
             f"<{limits['vpc_no_flow_logs_critical']} without flow logs",
             f"{vpc_no_fl} without flow logs",
             'Multiple VPCs have no flow logs enabled -- audit trail missing.')
    elif limits.get('vpc_no_flow_logs_warning') and vpc_no_fl >= limits['vpc_no_flow_logs_warning']:
        _add('WARNING', 'VPC Security', 'VPCs',
             f"<{limits['vpc_no_flow_logs_warning']} without flow logs",
             f"{vpc_no_fl} without flow logs",
             'Some VPCs are running without flow logs.')

    # 11. OpenSearch domains without encryption
    open_no_enc = resource_counts.get('OpenSearch_no_encryption', 0)
    if (limits.get('opensearch_unencrypted_critical') is not None
            and open_no_enc >= limits['opensearch_unencrypted_critical']):
        _add('CRITICAL', 'OpenSearch Security', 'OpenSearch Domains',
             f"<{limits['opensearch_unencrypted_critical']} unencrypted",
             f"{open_no_enc} unencrypted",
             'OpenSearch domains without encryption at rest detected.')
    elif (limits.get('opensearch_unencrypted_warning') is not None
          and open_no_enc >= limits['opensearch_unencrypted_warning']):
        _add('WARNING', 'OpenSearch Security', 'OpenSearch Domains',
             f"<{limits['opensearch_unencrypted_warning']} unencrypted",
             f"{open_no_enc} unencrypted",
             'Some OpenSearch domains are missing encryption at rest.')

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


def _build_health_record(result, error_msg=None):
    """
    Build a single health entry for the Discovery Health block.
    Called by the _run() closure inside run() -- not called directly.
    """
    if error_msg:
        return {'status': 'error', 'count': 0, 'error': error_msg}
    if isinstance(result, dict):
        count = sum(len(v) for v in result.values())
    elif isinstance(result, list):
        count = len(result)
    else:
        count = int(result or 0)
    return {'status': 'ok' if count > 0 else 'empty', 'count': count, 'error': None}


def _build_slack_blocks(
    alerts, discovery_summary, cost_summary, billing_estimate, forecast,
    ec2_by_region, rds_by_region, s3_buckets,
    lambda_by_region, dynamo_by_region, elb_by_region,
    ecs_by_region, elasticache_by_region, cloudfront_distributions,
    nat_by_region, vpc_by_region, eks_by_region,
    sqs_by_region, sns_by_region, opensearch_by_region,
    ecr_by_region, discovery_health,
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
                    f'Window: *{cost_window["start"]}* -> *{cost_window["end"]}* '
                    f'({cost_window["days"]} days)'
                )
            }]
        },
        {'type': 'divider'},
    ]

    # -- Cost snapshot ------------------------------------------------------
    if enable_cost_explorer and cost_summary and cost_summary.get('total_cost_usd') is not None:
        total_cost   = cost_summary['total_cost_usd']
        top_services = sorted(
            ((s, v) for s, v in cost_summary.get('by_service', {}).items() if v > 0),
            key=lambda x: x[1], reverse=True
        )[:5]
        top_lines = "\n".join(
            f'* {s}: *${v:.2f}*' for s, v in top_services
        ) or '_No data_'
        _safe_add_block(blocks, {
            'type': 'section',
            'fields': [
                {
                    'type': 'mrkdwn',
                    'text': (
                        f'*:moneybag: Actual Cost (CE)*\n*${total_cost:.2f}*\n'
                        f'_{cost_window["start"]} -> {cost_window["end"]}_'
                    )
                },
                {'type': 'mrkdwn', 'text': f'*:bar_chart: Top Services (CE)*\n{top_lines}'},
            ]
        })
    else:
        total_est = billing_estimate.get('total_estimated_usd')
        est_str   = f'*${total_est:.2f}*' if total_est is not None else '_Unavailable_'
        svc_lines = '\n'.join(
            f'* {s}: *${v:.2f}*'
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
                        f'*:moneybag: Est. MTD Charges (Free)*\n{est_str}\n'
                        f'_{billing_estimate.get("note", "")}_'
                    )
                },
                {'type': 'mrkdwn', 'text': f'*:bar_chart: Top Services (Est.)*\n{svc_lines}'},
            ]
        })

    # -- Forecast section ---------------------------------------------------
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
            f'\nCE remaining: *${ce_fc["remaining_forecast_usd"]:.2f}*'
            f'\nRange: ${ce_fc["lower_bound_usd"]:.2f} - ${ce_fc["upper_bound_usd"]:.2f}'
        )

    svc_proj_lines = '\n'.join(
        f'* {s}: *${v:.2f}*'
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
                    f'*Projected Month-End*\n{proj_text}\n'
                    f'_${daily:.2f}/day x {total_d} days_\n'
                    f'_{forecast.get("note", "")}_'
                )
            },
            {
                'type': 'mrkdwn',
                'text': (
                    f'*:calendar: Month Progress*\n'
                    f'Day *{elapsed}* of *{total_d}*\n'
                    f'_{remaining} days remaining_\n\n'
                    f'*Top Service Projections*\n{svc_proj_lines}'
                )
            },
        ]
    })

    # -- Resource summary + Discovery Health -------------------------------
    _safe_add_block(blocks, {'type': 'divider'})
    res_lines = '\n'.join(
        f'* {svc}: *{cnt}*'
        for svc, cnt in discovery_summary.get('resource_counts', {}).items()
        if cnt > 0
    ) or '_No active resources found_'

    _safe_add_block(blocks, {
        'type': 'section',
        'fields': [
            {
                'type': 'mrkdwn',
                'text': (
                    f'*:globe_with_meridians: Regions Scanned*\n'
                    f'{discovery_summary.get("regions_scanned", 0)} total | '
                    f'{discovery_summary.get("regions_with_resources", 0)} with resources'
                )
            },
            {'type': 'mrkdwn', 'text': f'*:package: Active Resource Counts*\n{res_lines}'},
        ]
    })

    # -- Discovery Health -- always shown so silent failures are visible -----
    _safe_add_block(blocks, {'type': 'divider'})
    _safe_add_block(blocks, {
        'type': 'section',
        'text': {'type': 'mrkdwn', 'text': '*:stethoscope: Discovery Health*'}
    })

    STATUS_ICON = {'ok': ':white_check_mark:', 'empty': ':white_circle:', 'error': ':x:'}
    health_lines = []
    for svc, info in discovery_health.items():
        icon  = STATUS_ICON.get(info['status'], ':question:')
        count = info['count']
        err   = f'  _{info["error"][:60]}_' if info.get('error') else ''
        health_lines.append(f'{icon} *{svc}*: {count} found{err}')

    # Split into two columns
    mid   = (len(health_lines) + 1) // 2
    left  = '\n'.join(health_lines[:mid])  or '_none_'
    right = '\n'.join(health_lines[mid:]) or ''
    fields = [{'type': 'mrkdwn', 'text': left}]
    if right:
        fields.append({'type': 'mrkdwn', 'text': right})

    _safe_add_block(blocks, {'type': 'section', 'fields': fields})

    # -- EC2 ----------------------------------------------------------------
    if ec2_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:computer: EC2 Instances*'}
        })
        for region, instances in sorted(ec2_by_region.items()):
            lines = '\n'.join(
                f'  * *{i["Name"]}* | `{i["InstanceId"]}` | '
                f'`{i["InstanceType"]}` | _{i["State"]}_'
                for i in instances
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(instances)})\n{lines}'}
            })

    # -- RDS ----------------------------------------------------------------
    if rds_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:floppy_disk: RDS Instances*'}
        })
        for region, dbs in sorted(rds_by_region.items()):
            lines = '\n'.join(
                f'  * *{d["Identifier"]}* | {d["Engine"]} | '
                f'`{d["Class"]}` | {d["Storage"]} | _{d["Status"]}_'
                for d in dbs
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(dbs)})\n{lines}'}
            })

    # -- S3 -----------------------------------------------------------------
    if s3_buckets:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:bucket: S3 Buckets*'}
        })
        lines = '\n'.join(
            f'  * *{b["BucketName"]}* | `{b["Region"]}` | '
            f'{b["StorageHuman"]} ({b["ObjectCount"]:,} objects) | '
            f'Enc: {b["Encryption"]} | Access: {b["PublicAccess"]}'
            for b in s3_buckets
        )
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn',
                     'text': f'*All Regions* ({len(s3_buckets)})\n{lines}'}
        })

    # -- Lambda -------------------------------------------------------------
    if lambda_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:zap: Lambda Functions*'}
        })
        for region, fns in sorted(lambda_by_region.items()):
            lines = '\n'.join(
                f'  * *{f["FunctionName"]}* | {f["Runtime"]} | '
                f'{f["MemorySize"]}MB | {f["Timeout"]}s | {f["CodeSizeHuman"]}'
                for f in fns
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(fns)})\n{lines}'}
            })

    # -- DynamoDB -----------------------------------------------------------
    if dynamo_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:card_index_dividers: DynamoDB Tables*'}
        })
        for region, tables in sorted(dynamo_by_region.items()):
            lines = '\n'.join(
                f'  * *{t["TableName"]}* | {t["SizeHuman"]} | '
                f'{t["ItemCount"]:,} items | _{t["Status"]}_'
                for t in tables
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(tables)})\n{lines}'}
            })

    # -- Load Balancers (ALB / NLB / CLB) ----------------------------------
    if elb_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:scales: Load Balancers (ALB / NLB / CLB)*'}
        })
        for region, lbs in sorted(elb_by_region.items()):
            lines = '\n'.join(
                f'  * *{lb["Name"]}* | {lb["Type"]} | {lb["Scheme"]} | _{lb["State"]}_'
                for lb in lbs
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(lbs)})\n{lines}'}
            })

    # -- ECS ----------------------------------------------------------------
    if ecs_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:ship: ECS Clusters & Services*'}
        })
        for region, clusters in sorted(ecs_by_region.items()):
            cluster_lines = []
            for c in clusters:
                svc_summary = (
                    ', '.join(
                        f'{s["ServiceName"]} ({s["RunningCount"]}/{s["DesiredCount"]})'
                        for s in c['Services'][:3]
                    )
                    + ('...' if len(c['Services']) > 3 else '')
                ) if c['Services'] else '_(no services)_'
                cluster_lines.append(
                    f'  * *{c["ClusterName"]}* | _{c["Status"]}_ | '
                    f'Tasks: {c["RunningTasksCount"]} running / '
                    f'{c["PendingTasksCount"]} pending | '
                    f'Services: {c["ActiveServicesCount"]}\n'
                    f'    -> {svc_summary}'
                )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(clusters)})\n' + '\n'.join(cluster_lines)}
            })

    # -- ElastiCache --------------------------------------------------------
    if elasticache_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:zap: ElastiCache Clusters*'}
        })
        for region, clusters in sorted(elasticache_by_region.items()):
            lines = []
            for c in clusters:
                if c['Type'] == 'Redis':
                    enc_flag = (
                        ':lock:' if c.get('AtRestEncryption') and c.get('InTransitEncryption')
                        else ':unlock:'
                    )
                    lines.append(
                        f'  * *{c["Id"]}* | Redis | _{c["Status"]}_ | '
                        f'{c["NumNodeGroups"]} shard(s) | '
                        f'Multi-AZ: {c["MultiAZ"]} | {enc_flag} Enc'
                    )
                else:
                    lines.append(
                        f'  * *{c["Id"]}* | Memcached | _{c["Status"]}_ | '
                        f'{c["NumNodes"]} node(s) | {c.get("NodeType", "N/A")}'
                    )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(clusters)})\n' + '\n'.join(lines)}
            })

    # -- CloudFront ---------------------------------------------------------
    if cloudfront_distributions:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:cloud: CloudFront Distributions (CDN)*'}
        })
        lines = []
        for d in cloudfront_distributions:
            aliases = ', '.join(d['Aliases'][:2]) + (
                f' +{len(d["Aliases"]) - 2}' if len(d['Aliases']) > 2 else ''
            )
            lines.append(
                f'  * *{d["Id"]}* | _{d["Status"]}_ | '
                f'`{d["DomainName"]}`\n'
                f'    -> Aliases: {aliases} | '
                f'Origins: {", ".join(d["Origins"][:2])} | '
                f'Price: {d["PriceClass"]} | '
                f'Enabled: {d["Enabled"]}'
            )
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn',
                     'text': f'*Global* ({len(cloudfront_distributions)})\n' + '\n'.join(lines)}
        })

    # -- NAT Gateways -------------------------------------------------------
    if nat_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:arrows_counterclockwise: NAT Gateways*'}
        })
        for region, nats in sorted(nat_by_region.items()):
            lines = '\n'.join(
                f'  * *{n["Name"]}* | `{n["NatGatewayId"]}` | '
                f'{n["Type"]} | _{n["State"]}_ | '
                f'VPC: `{n["VpcId"]}` | '
                f'IPs: {", ".join(n["PublicIPs"]) or "N/A"}'
                for n in nats
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(nats)})\n{lines}'}
            })

    # -- VPCs ---------------------------------------------------------------
    if vpc_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:globe_with_meridians: VPCs*'}
        })
        for region, vpcs in sorted(vpc_by_region.items()):
            lines = '\n'.join(
                f'  * *{v["Name"]}* | `{v["VpcId"]}` | '
                f'`{v["CidrBlock"]}` | _{v["State"]}_ | '
                f'Subnets: {v["TotalSubnets"]} ({v["PublicSubnets"]} pub / '
                f'{v["PrivateSubnets"]} priv) | '
                f'Default: {v["IsDefault"]} | '
                f'FlowLogs: {":white_check_mark:" if v["FlowLogsEnabled"] else ":x:"}'
                for v in vpcs
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(vpcs)})\n{lines}'}
            })

    # -- EKS ----------------------------------------------------------------
    if eks_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:wheel_of_dharma: EKS Clusters*'}
        })
        for region, clusters in sorted(eks_by_region.items()):
            lines = []
            for c in clusters:
                ng_summary = (
                    ', '.join(
                        f'{ng["Name"]} ({ng["DesiredSize"]}x {ng["InstanceType"]})'
                        for ng in c['NodeGroups'][:3]
                    )
                    + ('...' if len(c['NodeGroups']) > 3 else '')
                ) if c['NodeGroups'] else '_(no managed node groups)_'
                lines.append(
                    f'  * *{c["ClusterName"]}* | k8s {c["Version"]} | '
                    f'_{c["Status"]}_ | {c["PlatformVersion"]} | '
                    f'Logging: {":white_check_mark:" if c["LoggingEnabled"] else ":x:"}\n'
                    f'    -> {ng_summary}'
                )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(clusters)})\n' + '\n'.join(lines)}
            })

    # -- SQS ----------------------------------------------------------------
    if sqs_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:mailbox: SQS Queues*'}
        })
        for region, queues in sorted(sqs_by_region.items()):
            lines = '\n'.join(
                f'  * *{q["QueueName"]}* | '
                f'{"FIFO" if q["IsFifo"] else "Standard"} | '
                f'Msgs: {q["ApproxMessages"]:,} | '
                f'In-flight: {q["InFlight"]:,} | '
                f'Retention: {q["RetentionDays"]}d'
                for q in queues
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(queues)})\n{lines}'}
            })

    # -- SNS ----------------------------------------------------------------
    if sns_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:bell: SNS Topics*'}
        })
        for region, topics in sorted(sns_by_region.items()):
            lines = '\n'.join(
                f'  * *{t["TopicName"]}* | '
                f'{"FIFO" if t["FifoTopic"] else "Standard"} | '
                f'Subs: {t["SubscriptionsConfirmed"]} confirmed / '
                f'{t["SubscriptionsPending"]} pending'
                for t in topics
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(topics)})\n{lines}'}
            })

    # -- OpenSearch ---------------------------------------------------------
    if opensearch_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:mag: OpenSearch Domains*'}
        })
        for region, domains in sorted(opensearch_by_region.items()):
            lines = '\n'.join(
                f'  * *{d["DomainName"]}* | {d["EngineVersion"]} | '
                f'_{d["Status"]}_ | '
                f'{d["InstanceCount"]}x `{d["InstanceType"]}` | '
                f'{d["VolumeGB"]}GB | '
                f'EncRest: {":lock:" if d["EncryptionAtRest"] else ":unlock:"} | '
                f'EncTransit: {":lock:" if d["NodeToNodeEncryption"] else ":unlock:"}'
                for d in domains
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(domains)})\n{lines}'}
            })

    # -- ECR ----------------------------------------------------------------
    if ecr_by_region:
        _safe_add_block(blocks, {'type': 'divider'})
        _safe_add_block(blocks, {
            'type': 'section',
            'text': {'type': 'mrkdwn', 'text': '*:whale: ECR Repositories*'}
        })
        for region, repos in sorted(ecr_by_region.items()):
            lines = '\n'.join(
                f'  * *{r["RepositoryName"]}* | '
                f'{r["ImageCount"]} images | {r["TotalSizeHuman"]} | '
                f'Tag: {r["TagMutability"]} | '
                f'Scan: {":white_check_mark:" if r["ScanOnPush"] else ":x:"} | '
                f'Lifecycle: {":white_check_mark:" if r["HasLifecyclePolicy"] else ":x:"} | '
                f'Enc: {r["EncryptionType"]}'
                for r in repos
            )
            _safe_add_block(blocks, {
                'type': 'section',
                'text': {'type': 'mrkdwn',
                         'text': f'*{region}* ({len(repos)})\n{lines}'}
            })

    # -- Alerts -------------------------------------------------------------
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
                        f" -- {alert['resource']}\n"
                        f">*Threshold:* {alert['threshold_label']}  |  "
                        f"*Actual:* {alert['actual_label']}\n"
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

        log_info("task", "initialize", "building_clients",
                 f"Initialising AWS clients in base region: {region}")

        ec2_base = _make_boto3_client('ec2', connection, region)
        regions  = _get_regions(ec2_base)

        log_info("task", "initialize", "regions_discovered",
                 f"Discovered {len(regions)} AWS regions")

        clients = {
            # Single-region / global clients
            'ec2_base':        ec2_base,
            'rds':             _make_boto3_client('rds',        connection, region),
            's3':              _make_boto3_client('s3',         connection, region),
            'ce':              _make_boto3_client('ce',         connection, 'us-east-1'),
            'cw':              _make_boto3_client('cloudwatch', connection, 'us-east-1'),
            # CloudFront is a global service -- single client in us-east-1
            'cloudfront':      _make_boto3_client('cloudfront', connection, 'us-east-1'),

            # Regional client maps
            'ec2_regional':         _build_regional_clients('ec2',           regions, connection),
            'lambda_regional':      _build_regional_clients('lambda',        regions, connection),
            'dynamo_regional':      _build_regional_clients('dynamodb',      regions, connection),
            'elbv2_regional':       _build_regional_clients('elbv2',         regions, connection),
            'ecs_regional':         _build_regional_clients('ecs',           regions, connection),
            'elasticache_regional': _build_regional_clients('elasticache',   regions, connection),
            'eks_regional':         _build_regional_clients('eks',           regions, connection),
            'sqs_regional':         _build_regional_clients('sqs',           regions, connection),
            'sns_regional':         _build_regional_clients('sns',           regions, connection),
            'opensearch_regional':  _build_regional_clients('opensearch',    regions, connection),
            'ecr_regional':         _build_regional_clients('ecr',           regions, connection),

            'regions': regions,
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

        # -- Discovery health tracker ---------------------------------------
        # Wraps every discovery call: records count + ok/empty/error status.
        # Results are shown in the Slack Discovery Health block so silent
        # permission errors or service unavailability are immediately visible.
        discovery_health = {}

        def _run(label, fn, *args, _empty=None):
            """Call fn(*args), record health, never raise."""
            _default = [] if _empty == 'list' else {}
            try:
                result = fn(*args)
                discovery_health[label] = _build_health_record(result)
                return result
            except Exception as exc:
                discovery_health[label] = _build_health_record(None, str(exc))
                log_error("task", "run", f"discover_{label.lower().replace(' ','_')}", str(exc))
                return _default

        # -- Original services ----------------------------------------------
        log_info("task", "run", "discovering_ec2", "Fetching EC2 instances")
        ec2_by_region = _run('EC2', _discover_ec2, client['ec2_regional'])

        log_info("task", "run", "discovering_rds", "Fetching RDS instances")
        rds_by_region = _run('RDS', _discover_rds, client['rds'])

        log_info("task", "run", "discovering_s3",
                 "Fetching S3 buckets + storage sizes via ListObjectsV2 (free)")
        s3_buckets = _run('S3', _discover_s3, client['s3'], client['cw'], _empty='list')

        log_info("task", "run", "discovering_lambda", "Fetching Lambda functions")
        lambda_by_region = _run('Lambda', _discover_lambda, client['lambda_regional'])

        log_info("task", "run", "discovering_dynamodb", "Fetching DynamoDB tables")
        dynamo_by_region = _run('DynamoDB', _discover_dynamodb, client['dynamo_regional'])

        log_info("task", "run", "discovering_elbv2",
                 "Fetching Load Balancers (ALB / NLB / GLB)")
        elb_by_region = _run('LoadBalancer', _discover_elbv2, client['elbv2_regional'])

        # -- New services ---------------------------------------------------
        log_info("task", "run", "discovering_ecs",
                 "Fetching ECS clusters, services, and task counts")
        ecs_by_region = _run('ECS', _discover_ecs, client['ecs_regional'])

        log_info("task", "run", "discovering_ecr", "Fetching ECR repositories")
        ecr_by_region = _run('ECR', _discover_ecr, client['ecr_regional'])

        log_info("task", "run", "discovering_elasticache",
                 "Fetching ElastiCache replication groups and cache clusters")
        elasticache_by_region = _run(
            'ElastiCache', _discover_elasticache, client['elasticache_regional'])

        log_info("task", "run", "discovering_cloudfront",
                 "Fetching CloudFront distributions (global)")
        cloudfront_distributions = _run(
            'CloudFront', _discover_cloudfront, client['cloudfront'], _empty='list')

        log_info("task", "run", "discovering_nat", "Fetching NAT Gateways")
        nat_by_region = _run('NAT Gateways', _discover_nat_gateways, client['ec2_regional'])

        log_info("task", "run", "discovering_vpc",
                 "Fetching VPCs, subnets, and flow log status")
        vpc_by_region = _run('VPC', _discover_vpcs, client['ec2_regional'])

        log_info("task", "run", "discovering_eks",
                 "Fetching EKS clusters and node groups")
        eks_by_region = _run('EKS', _discover_eks, client['eks_regional'])

        log_info("task", "run", "discovering_sqs", "Fetching SQS queues")
        sqs_by_region = _run('SQS', _discover_sqs, client['sqs_regional'])

        log_info("task", "run", "discovering_sns", "Fetching SNS topics")
        sns_by_region = _run('SNS', _discover_sns, client['sns_regional'])

        log_info("task", "run", "discovering_opensearch", "Fetching OpenSearch domains")
        opensearch_by_region = _run(
            'OpenSearch', _discover_opensearch, client['opensearch_regional'])

        # -- Billing --------------------------------------------------------
        log_info("task", "run", "billing_estimate",
                 "Fetching CloudWatch billing estimate (free)")
        billing_estimate = _get_billing_estimate(client['cw'])

        # -- Cost Explorer + Forecast ---------------------------------------
        cost_summary = None
        if enable_cost_explorer:
            log_info("task", "run", "fetching_costs",
                     f"CE query: {cost_start} -> {cost_end} [BILLED $0.02]")
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
                     "CE disabled -- free CW estimate in use. "
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

        # -- Aggregate resource counts --------------------------------------
        all_ec2    = [i for lst in ec2_by_region.values()    for i in lst]
        all_rds    = [i for lst in rds_by_region.values()    for i in lst]
        all_lambda = [i for lst in lambda_by_region.values() for i in lst]
        all_dynamo = [i for lst in dynamo_by_region.values() for i in lst]
        all_elb    = [i for lst in elb_by_region.values()    for i in lst]
        all_ecs    = [c for lst in ecs_by_region.values()    for c in lst]
        all_ecr    = [r for lst in ecr_by_region.values()    for r in lst]
        all_ec     = [c for lst in elasticache_by_region.values() for c in lst]
        all_nat    = [n for lst in nat_by_region.values()    for n in lst]
        all_vpc    = [v for lst in vpc_by_region.values()    for v in lst]
        all_eks    = [c for lst in eks_by_region.values()    for c in lst]
        all_sqs    = [q for lst in sqs_by_region.values()    for q in lst]
        all_sns    = [t for lst in sns_by_region.values()    for t in lst]
        all_os     = [d for lst in opensearch_by_region.values() for d in lst]

        resource_counts_raw = {
            'EC2':                    len(all_ec2),
            'EC2_running':            sum(1 for i in all_ec2 if i['State'] == 'running'),
            'RDS':                    len(all_rds),
            'S3':                     len(s3_buckets),
            'Lambda':                 len(all_lambda),
            'DynamoDB':               len(all_dynamo),
            'LoadBalancer':           len(all_elb),
            'ECS_clusters':           len(all_ecs),
            'ECS_services':           sum(c['ActiveServicesCount'] for c in all_ecs),
            'ECS_tasks_running':      sum(c['RunningTasksCount'] for c in all_ecs),
            'ECR_repositories':       len(all_ecr),
            'ECR_images':             sum(r['ImageCount'] for r in all_ecr),
            'ElastiCache':            len(all_ec),
            'CloudFront':             len(cloudfront_distributions),
            'NAT_gateways':           len(all_nat),
            'VPC':                    len(all_vpc),
            'VPC_no_flow_logs':       sum(1 for v in all_vpc if not v['FlowLogsEnabled']),
            'EKS_clusters':           len(all_eks),
            'EKS_node_groups':        sum(c['NodeGroupCount'] for c in all_eks),
            'SQS_queues':             len(all_sqs),
            'SNS_topics':             len(all_sns),
            'OpenSearch':             len(all_os),
            'OpenSearch_no_encryption': sum(1 for d in all_os if not d['EncryptionAtRest']),
        }
        resource_counts = {k: v for k, v in resource_counts_raw.items() if v > 0}

        log_info("task", "run", "resource_counts",
                 f"Active resources: {json.dumps(resource_counts)}")

        discovery_summary = {
            'regions_scanned':        len(client['regions']),
            'regions_with_resources': len(set(
                list(ec2_by_region)    + list(rds_by_region)     +
                list(lambda_by_region) + list(dynamo_by_region)  +
                list(elb_by_region)    + list(ecs_by_region)     +
                list(ecr_by_region)    +
                list(elasticache_by_region) + list(nat_by_region) +
                list(vpc_by_region)    + list(eks_by_region)     +
                list(sqs_by_region)    + list(sns_by_region)     +
                list(opensearch_by_region)
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
        if slack_webhook:
            # Send on every run -- not just on alerts.
            # The Discovery Health block makes every run informative
            # even when no thresholds are breached.
            if not alerts:
                log_info("task", "run", "slack_no_alerts",
                         "No thresholds breached -- sending summary-only notification")
            else:
                log_info("task", "run", "sending_slack",
                         f"Sending Slack notification for {len(alerts)} alert(s)")
            blocks = _build_slack_blocks(
                alerts, discovery_summary,
                cost_summary if enable_cost_explorer else None,
                billing_estimate, forecast,
                ec2_by_region, rds_by_region, s3_buckets,
                lambda_by_region, dynamo_by_region, elb_by_region,
                ecs_by_region, elasticache_by_region, cloudfront_distributions,
                nat_by_region, vpc_by_region, eks_by_region,
                sqs_by_region, sns_by_region, opensearch_by_region,
                ecr_by_region, discovery_health,
                cost_summary['window'], enable_cost_explorer,
            )
            _send_slack_notification(slack_webhook, blocks)
            slack_sent = True
        else:
            log_error("task", "run", "slack_webhook_missing",
                      "No Slack webhook URL configured -- notification skipped")

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
                'discovery_health':     discovery_health,
                'resources': {
                    **(({'ec2':                ec2_by_region}           if ec2_by_region           else {})),
                    **(({'rds':                rds_by_region}           if rds_by_region           else {})),
                    **(({'s3':                 s3_buckets}              if s3_buckets              else {})),
                    **(({'lambda':             lambda_by_region}        if lambda_by_region        else {})),
                    **(({'dynamodb':           dynamo_by_region}        if dynamo_by_region        else {})),
                    **(({'load_balancer':      elb_by_region}           if elb_by_region           else {})),
                    **(({'ecs':                ecs_by_region}           if ecs_by_region           else {})),
                    **(({'ecr':                ecr_by_region}           if ecr_by_region           else {})),
                    **(({'elasticache':        elasticache_by_region}   if elasticache_by_region   else {})),
                    **(({'cloudfront':         cloudfront_distributions} if cloudfront_distributions else {})),
                    **(({'nat_gateways':       nat_by_region}           if nat_by_region           else {})),
                    **(({'vpcs':               vpc_by_region}           if vpc_by_region           else {})),
                    **(({'eks':                eks_by_region}           if eks_by_region           else {})),
                    **(({'sqs':                sqs_by_region}           if sqs_by_region           else {})),
                    **(({'sns':                sns_by_region}           if sns_by_region           else {})),
                    **(({'opensearch':         opensearch_by_region}    if opensearch_by_region    else {})),
                }
            }
        }

        log_info("task", "run", "complete",
                 f"Discovery complete -- active: {list(result['result']['resources'].keys())} | "
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
                     "Synchronous operation -- no polling required")
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

        log_info("task", "finish", "final_status",
                 f"Task {task_laui} finished with status: {status}")

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
                     f"Window: {window.get('start')} -> {window.get('end')} | "
                     f"Forecast source: {forecast.get('source', 'N/A')} | "
                     f"Projected month-end: ${forecast.get('projected_month_end_usd', 'N/A')}")
        else:
            log_error("task", "finish", "operation_failed",
                      completion_details.get('message', 'No message'))

        log_info("task", "finish", "cleanup_complete",
                 f"Cleanup done for task: {task_laui}")

    except Exception as e:
        log_error("task", "finish", "cleanup_error", str(e))'''}

bashblock = {'main.sh':
            '''#!/bin/bash
pip install boto3>=1.28.0
pip install botocore>=1.31.0
pip install requests>=2.31.0

echo "Dependencies installed successfully"'''}

connection = {
  "region": "us-east-1",
  "aws_access_key_id": "",
  "aws_secret_access_key": "",
  "session_token": "",
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
        "Amazon Elastic Compute Cloud - Compute": {
          "warning_usd": 200,
          "critical_usd": 400
        },
        "Amazon Relational Database Service": {
          "warning_usd": 100,
          "critical_usd": 200
        },
        "AWS Lambda": {
          "warning_usd": 20,
          "critical_usd": 50
        },
        "Amazon Simple Storage Service": {
          "warning_usd": 30,
          "critical_usd": 60
        },
        "Amazon CloudFront": {
          "warning_usd": 30,
          "critical_usd": 75
        },
        "Amazon ElastiCache": {
          "warning_usd": 80,
          "critical_usd": 150
        },
        "Amazon Elastic Container Service": {
          "warning_usd": 100,
          "critical_usd": 200
        },
        "Amazon Elastic Kubernetes Service": {
          "warning_usd": 150,
          "critical_usd": 300
        },
        "Amazon Simple Queue Service": {
          "warning_usd": 10,
          "critical_usd": 25
        },
        "Amazon Simple Notification Service": {
          "warning_usd": 5,
          "critical_usd": 15
        },
        "Amazon OpenSearch Service": {
          "warning_usd": 60,
          "critical_usd": 120
        },
        "Amazon Virtual Private Cloud": {
          "warning_usd": 50,
          "critical_usd": 100
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
        },
        "ap-southeast-1": {
          "warning_usd": 150,
          "critical_usd": 300
        }
      },
      "resource_count_limits": {
        "EC2": {"warning": 20, "critical": 40},
        "RDS": {"warning": 10, "critical": 20},
        "Lambda": {"warning": 50, "critical": 100},
        "DynamoDB": {"warning": 20, "critical": 40},
        "LoadBalancer": {"warning": 10, "critical": 20},
        "ECS_clusters": {"warning": 10, "critical": 25},
        "ECS_services": {"warning": 50, "critical": 100},
        "ECR_repositories": {"warning": 20, "critical": 50},
        "ElastiCache": {"warning": 5, "critical": 10},
        "CloudFront": {"warning": 10, "critical": 25},
        "NAT_gateways": {"warning": 5, "critical": 10},
        "VPC": {"warning": 10, "critical": 20},
        "EKS_clusters": {"warning": 5, "critical": 10},
        "EKS_node_groups": {"warning": 15, "critical": 30},
        "SQS_queues": {"warning": 30, "critical": 60},
        "SNS_topics": {"warning": 20, "critical": 40},
        "OpenSearch": {"warning": 3, "critical": 6}
      },
      "ec2_running_warning": 10,
      "ec2_running_critical": 25,
      "s3_total_warning": 20,
      "s3_total_critical": 50,
      "s3_unencrypted_warning": 1,
      "s3_unencrypted_critical": 3,
      "s3_public_warning": 1,
      "s3_public_critical": 3,
      "ecs_tasks_warning": 50,
      "ecs_tasks_critical": 100,
      "vpc_no_flow_logs_warning": 1,
      "vpc_no_flow_logs_critical": 3,
      "opensearch_unencrypted_warning": 1,
      "opensearch_unencrypted_critical": 2
    }
  }
}

prompt = (
    "Discover all active AWS resources across 16 services -- EC2, RDS, S3, Lambda, DynamoDB, "
    "ALB/NLB (ELBv2), ECS (clusters + services + tasks), ECR (repositories + image counts), "
    "ElastiCache (Redis + Memcached), CloudFront, NAT Gateways, VPCs (subnets + flow logs), "
    "EKS (clusters + node groups), SQS, SNS, and OpenSearch -- across all enabled AWS regions. "
    "Always fetches a free CloudWatch MTD billing estimate and computes a linear month-end cost forecast. "
    "Cost Explorer is opt-in via enable_cost_explorer=true (billed ~$0.03/run) for exact per-service "
    "and per-region breakdowns plus a CE native forecast. S3 storage sizes are calculated via "
    "ListObjectsV2 at no charge. Evaluates configurable warning/critical thresholds for total cost, "
    "per-service cost, per-region cost, resource counts, running EC2 and ECS task counts, S3 "
    "encryption and public-access posture, VPCs without flow logs, and OpenSearch encryption at rest. "
    "Sends a Slack Block Kit notification on every run when a webhook is configured -- including a "
    "Discovery Health panel showing every service as found / empty / error so missing IAM permissions "
    "are immediately visible. Auth: IAM role via STS first, fallback to explicit access keys."
)

install_docs = """# AWSResourceDiscoveryCostAnalysis -- Install Guide

## Dependencies

    pip install boto3>=1.28.0
    pip install botocore>=1.31.0
    pip install requests>=2.31.0

## AWS IAM Permissions Required

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "sts:GetCallerIdentity",
            "ec2:DescribeRegions",
            "ec2:DescribeInstances",
            "ec2:DescribeNatGateways",
            "ec2:DescribeVpcs",
            "ec2:DescribeSubnets",
            "ec2:DescribeInternetGateways",
            "ec2:DescribeFlowLogs",
            "rds:DescribeDBInstances",
            "s3:ListAllMyBuckets",
            "s3:ListBucket",
            "s3:GetBucketLocation",
            "s3:GetEncryptionConfiguration",
            "s3:GetBucketPublicAccessBlock",
            "lambda:ListFunctions",
            "dynamodb:ListTables",
            "dynamodb:DescribeTable",
            "elasticloadbalancing:DescribeLoadBalancers",
            "ecs:ListClusters",
            "ecs:DescribeClusters",
            "ecs:ListServices",
            "ecs:DescribeServices",
            "ecr:DescribeRepositories",
            "ecr:DescribeImages",
            "ecr:GetLifecyclePolicy",
            "elasticache:DescribeReplicationGroups",
            "elasticache:DescribeCacheClusters",
            "cloudfront:ListDistributions",
            "eks:ListClusters",
            "eks:DescribeCluster",
            "eks:ListNodegroups",
            "eks:DescribeNodegroup",
            "sqs:ListQueues",
            "sqs:GetQueueAttributes",
            "sns:ListTopics",
            "sns:GetTopicAttributes",
            "es:ListDomainNames",
            "es:DescribeDomains",
            "cloudwatch:GetMetricStatistics",
            "ce:GetCostAndUsage",
            "ce:GetCostForecast"
          ],
          "Resource": "*"
        }
      ]
    }

Note: IAM actions for OpenSearch use the legacy es: namespace (AWS kept it after renaming
the service). The boto3 client name is opensearch -- both are correct and intentional.

## Auth Setup

| Method        | How                                                           |
|---------------|---------------------------------------------------------------|
| IAM role      | Attach role to EC2/ECS -- leave connection keys blank          |
| Access keys   | Set aws_access_key_id and aws_secret_access_key in connection |
| Session token | Optionally add session_token for temporary credentials        |

IAM role is always attempted first via sts:GetCallerIdentity. Explicit keys are
only used if the role probe fails.

## Slack Setup

Provide a Slack Incoming Webhook URL in the connection field slack_webhook_url.
A notification is sent on every run -- not only when thresholds are breached.
Every message includes a Discovery Health panel showing all 16 services with
their found / empty / error status so IAM permission gaps are immediately visible.
"""

guide_docs = """# AWSResourceDiscoveryCostAnalysis -- Operator Guide

## What It Does

Scans all AWS regions for active resources across 16 services and produces a unified
cost and inventory report. Computes a free CloudWatch billing estimate and a linear
month-end spend forecast on every run. Optionally queries Cost Explorer for exact
per-service and per-region cost breakdowns. Evaluates all findings against configurable
warning/critical thresholds and sends a Slack Block Kit notification on every run.

A Discovery Health panel is always included in the Slack message, showing every service
as found / empty / error -- so IAM permission failures never silently hide resources.

---

## Services Discovered

| Service       | What Is Captured                                                   |
|---------------|--------------------------------------------------------------------|
| EC2           | Instance ID, type, state, IPs, VPC, key name                      |
| RDS           | Engine, class, storage, multi-AZ, status (base region only)        |
| S3            | Storage size (ListObjectsV2), encryption, public access block      |
| Lambda        | Runtime, memory, timeout, code size                                |
| DynamoDB      | Table size, item count, status                                     |
| ELBv2         | ALB / NLB / GLB -- type, scheme, DNS name, state                   |
| ECS           | Clusters, services (running/desired/pending counts), task counts   |
| ECR           | Image count, total size, scan-on-push, lifecycle policy, tag mutability |
| ElastiCache   | Redis replication groups (shards, encryption, failover) + Memcached |
| CloudFront    | Distributions, aliases, origins, price class, HTTPS config        |
| NAT Gateways  | State, type (public/private), VPC, public IPs                     |
| VPCs          | CIDR, subnet counts (public/private split), IGWs, flow log status |
| EKS           | Clusters, k8s version, node groups (instance type, scaling config) |
| SQS           | Message depth, in-flight, retention period, FIFO detection        |
| SNS           | Topics, confirmed/pending subscriptions, FIFO detection           |
| OpenSearch    | Engine version, instance type/count, encryption at rest + transit |

---

## Auth

1. IAM role -- tried first via sts:GetCallerIdentity. Leave connection keys blank.
2. Access keys -- fallback if role probe fails. Set in connection.

---

## Connection

    {
      "region": "us-east-1",
      "aws_access_key_id": "",        // optional -- omit when using IAM role
      "aws_secret_access_key": "",    // optional -- omit when using IAM role
      "session_token": "",            // optional -- for temporary credentials
      "slack_webhook_url": "https://hooks.slack.com/services/..."
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

| Field                  | Required | Default | Description                                                          |
|------------------------|----------|---------|----------------------------------------------------------------------|
| enable_cost_explorer   | No       | false   | Enable Cost Explorer queries (~$0.03/run). Free CW estimate if off   |
| cost_lookback_days     | No       | 30      | Days to look back when no explicit dates are provided                |
| cost_start_date        | No       | --       | Explicit start date YYYY-MM-DD. Overrides lookback                   |
| cost_end_date          | No       | today   | Explicit end date YYYY-MM-DD. Used with cost_start_date              |
| cost_use_current_month | No       | false   | Use calendar month-to-date. Overrides all other date fields          |
| warning_limits         | No       | {}      | Threshold config -- see Threshold Reference below                     |

---

## Cost Window Priority

1. cost_use_current_month=true  ->  month start to today
2. cost_start_date set           ->  explicit range
3. fallback                      ->  today minus cost_lookback_days

---

## Threshold Reference (warning_limits)

    {
      // Total account spend
      "total_cost_warning_usd": 500,
      "total_cost_critical_usd": 1000,

      // Per-service spend (requires enable_cost_explorer=true)
      "service_cost_limits": {
        "Amazon Elastic Compute Cloud - Compute": { "warning_usd": 200, "critical_usd": 400 },
        "Amazon Elastic Container Service":       { "warning_usd": 100, "critical_usd": 200 },
        "Amazon ElastiCache":                     { "warning_usd": 80,  "critical_usd": 150 }
      },

      // Per-region spend (requires enable_cost_explorer=true)
      "region_cost_limits": {
        "us-east-1": { "warning_usd": 300, "critical_usd": 600 }
      },

      // Resource count limits (uses keys from resource_counts output)
      "resource_count_limits": {
        "EC2":             { "warning": 20,  "critical": 40  },
        "ECS_clusters":    { "warning": 10,  "critical": 25  },
        "ECR_repositories": { "warning": 20, "critical": 50  },
        "EKS_clusters":    { "warning": 5,   "critical": 10  },
        "SQS_queues":      { "warning": 30,  "critical": 60  }
      },

      // EC2-specific
      "ec2_running_warning": 10,
      "ec2_running_critical": 25,

      // S3-specific
      "s3_total_warning": 20,        "s3_total_critical": 50,
      "s3_unencrypted_warning": 1,   "s3_unencrypted_critical": 3,
      "s3_public_warning": 1,        "s3_public_critical": 3,

      // ECS running tasks
      "ecs_tasks_warning": 50,
      "ecs_tasks_critical": 100,

      // VPC security -- flow logs
      "vpc_no_flow_logs_warning": 1,
      "vpc_no_flow_logs_critical": 3,

      // OpenSearch encryption at rest
      "opensearch_unencrypted_warning": 1,
      "opensearch_unencrypted_critical": 2
    }

service_cost_limits and region_cost_limits are silently skipped when enable_cost_explorer=false.

---

## Output (on success)

    {
      "discovery_summary": {
        "regions_scanned": 17,
        "regions_with_resources": 5,
        "resource_counts": { "EC2": 5, "ECR_repositories": 3, "VPC": 17, ... },
        "timestamp": "2026-04-12T17:45:00"
      },
      "cost_summary":     { "total_cost_usd": 48.75, "by_service": {}, "by_region": {} },
      "billing_estimate": { "total_estimated_usd": null, "by_service": {} },
      "forecast":         { "projected_month_end_usd": 121.88, "daily_rate_usd": 4.06 },
      "alerts":           [ { "severity": "CRITICAL", "category": "Total Cost", ... } ],
      "slack_sent":       true,
      "discovery_health": {
        "EC2":        { "status": "ok",    "count": 5, "error": null },
        "VPC":        { "status": "ok",    "count": 17, "error": null },
        "EKS":        { "status": "empty", "count": 0, "error": null },
        "OpenSearch": { "status": "error", "count": 0, "error": "AccessDenied..." }
      },
      "resources": { "ec2": {}, "s3": [], "ecs": {}, "ecr": {}, "vpcs": {}, ... }
    }

---

## Edge Cases

No thresholds configured:
  Discovery and cost data still run fully. Slack is sent with health panel but no alert section.

enable_cost_explorer=false (default):
  CloudWatch EstimatedCharges fetched at no cost. Forecast uses CW data.
  service_cost_limits and region_cost_limits thresholds are skipped.

No Slack webhook:
  Alerts and discovery data are still computed and returned in output.
  Notification is skipped with a logged warning.

IAM role unavailable and no keys provided:
  RuntimeError raised in initialize(). Task fails immediately with a clear message.

Service shows error in Discovery Health:
  The most common cause is a missing IAM permission. Check the error string in
  discovery_health[service].error for the exact AccessDenied action.

RDS cross-region:
  _discover_rds uses a single regional client (base region). RDS instances in
  other regions are not discovered. Use a separate task per region if needed.

S3 buckets with many objects:
  ListObjectsV2 paginates fully per bucket. Large buckets increase runtime linearly.
"""

description = (
    "Scans your entire AWS account across all active regions and returns a complete inventory "
    "of infrastructure across 16 services -- EC2, RDS, S3, Lambda, ECS, ECR, EKS, ElastiCache, "
    "CloudFront, NAT Gateways, VPCs, SQS, SNS, OpenSearch, DynamoDB, and Load Balancers. "
    "Tracks month-to-date spend with per-service and per-region breakdowns, and projects month-end "
    "cost using a linear daily-rate forecast. Evaluates configurable warning and critical thresholds "
    "for cost, resource counts, and security posture (unencrypted S3, public buckets, VPCs without "
    "flow logs, OpenSearch without encryption). Sends a Slack notification on every run containing "
    "the full resource inventory, cost summary, forecast, and a Discovery Health panel that shows "
    "which services were found, empty, or errored -- so missing permissions are always visible at a glance."
)

publisher = "LeastActionLabs"

metadata = {
    "service": (
        "EC2, RDS, S3, Lambda, DynamoDB, ELBv2, ECS, ECR, ElastiCache, "
        "CloudFront, NAT Gateway, VPC, EKS, SQS, SNS, OpenSearch, "
        "CloudWatch, Cost Explorer"
    ),
    "category": "FinOps",
    "tags": [
        "cost", "billing", "discovery", "inventory",
        "ec2", "rds", "s3", "lambda", "dynamodb", "elb",
        "ecs", "ecr", "eks", "elasticache", "cloudfront",
        "nat", "vpc", "sqs", "sns", "opensearch",
        "cloudwatch", "forecast", "slack", "alerts", "aws", "finops"
    ],
    "airflow_equivalent": "BashOperator"
}

version_details = {"version": "2.0.0", "core": ["0.*"]}

verified = False

status = "draft"

publisher_notes = """## Publisher Notes

V2 of the resource discovery and billing operator. Cost Explorer is opt-in (~0.03 USD/run when enabled). CloudWatch billing estimate is always free. Slack Block Kit notifications are sent on threshold violations. IAM role is tried first; falls back to explicit keys. The payload uses a data envelope (payload.data) for configuration -- this is intentional for this operator.
"""

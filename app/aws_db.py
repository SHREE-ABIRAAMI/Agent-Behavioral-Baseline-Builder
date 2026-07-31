import json
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import redis
from app import config

logger = logging.getLogger("agent_baseline.aws")

# Redis Connection Initialization
_redis_client = None

def get_redis_client():
    global _redis_client
    if not config.REDIS_HOST:
        return None
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=2.0
            )
            # Ping connection to verify
            _redis_client.ping()
            logger.info("Successfully connected to Redis instance.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
    return _redis_client

# DynamoDB Resource Initialization
_dynamodb_resource = None

def get_dynamodb_resource():
    global _dynamodb_resource
    if _dynamodb_resource is None:
        try:
            session = boto3.Session()
            if config.DYNAMODB_ENDPOINT:
                _dynamodb_resource = session.resource(
                    'dynamodb',
                    region_name=config.AWS_REGION,
                    endpoint_url=config.DYNAMODB_ENDPOINT
                )
            else:
                _dynamodb_resource = session.resource(
                    'dynamodb',
                    region_name=config.AWS_REGION
                )
            logger.info("Successfully initialized AWS DynamoDB resource.")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB resource: {e}")
            _dynamodb_resource = None
    return _dynamodb_resource

# Create DynamoDB Tables if they don't exist
def init_dynamodb_tables():
    db = get_dynamodb_resource()
    if not db:
        return
        
    tables_config = [
        {
            "TableName": "agent_baseline_agents",
            "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}]
        },
        {
            "TableName": "agent_baseline_baselines",
            "KeySchema": [
                {"AttributeName": "agent_id", "KeyType": "HASH"},
                {"AttributeName": "cluster_id", "KeyType": "RANGE"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "agent_id", "AttributeType": "S"},
                {"AttributeName": "cluster_id", "AttributeType": "N"}
            ]
        },
        {
            "TableName": "agent_baseline_intent_clusters",
            "KeySchema": [
                {"AttributeName": "agent_id", "KeyType": "HASH"},
                {"AttributeName": "cluster_id", "KeyType": "RANGE"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "agent_id", "AttributeType": "S"},
                {"AttributeName": "cluster_id", "AttributeType": "N"}
            ]
        },
        {
            "TableName": "agent_baseline_sessions",
            "KeySchema": [
                {"AttributeName": "agent_id", "KeyType": "HASH"},
                {"AttributeName": "id", "KeyType": "RANGE"} # session_id
            ],
            "AttributeDefinitions": [
                {"AttributeName": "agent_id", "AttributeType": "S"},
                {"AttributeName": "id", "AttributeType": "S"}
            ]
        },
        {
            "TableName": "agent_baseline_drift_alerts",
            "KeySchema": [
                {"AttributeName": "agent_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": "agent_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "S"}
            ]
        }
    ]

    for tc in tables_config:
        try:
            logger.info(f"Checking DynamoDB table: {tc['TableName']}...")
            db.meta.client.describe_table(TableName=tc['TableName'])
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info(f"Creating DynamoDB table: {tc['TableName']}...")
                db.create_table(
                    TableName=tc['TableName'],
                    KeySchema=tc['KeySchema'],
                    AttributeDefinitions=tc['AttributeDefinitions'],
                    ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                )
            else:
                logger.error(f"Error describing DynamoDB table {tc['TableName']}: {e}")

# DynamoDB Operations Implementation

def dynamo_save_agent(agent_id: str, name: str, description: str, system_prompt: str, tools: list):
    db = get_dynamodb_resource()
    if not db:
        return
    table = db.Table("agent_baseline_agents")
    table.put_item(Item={
        "id": agent_id,
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "tools": json.dumps(tools),
        "created_at": datetime.utcnow().isoformat()
    })

def dynamo_get_agent(agent_id: str):
    db = get_dynamodb_resource()
    if not db:
        return None
    table = db.Table("agent_baseline_agents")
    try:
        response = table.get_item(Key={"id": agent_id})
        item = response.get("Item")
        if item:
            item["tools"] = json.loads(item["tools"])
            return item
    except ClientError as e:
        logger.error(f"Error fetching agent: {e}")
    return None

def dynamo_list_agents():
    db = get_dynamodb_resource()
    if not db:
        return []
    table = db.Table("agent_baseline_agents")
    try:
        response = table.scan()
        items = response.get("Items", [])
        for item in items:
            item["tools"] = json.loads(item["tools"])
        return items
    except ClientError as e:
        logger.error(f"Error scanning agents: {e}")
    return []

def dynamo_save_baseline(agent_id: str, cluster_id: int, fingerprint: dict):
    db = get_dynamodb_resource()
    if not db:
        return
    table = db.Table("agent_baseline_baselines")
    table.put_item(Item={
        "agent_id": agent_id,
        "cluster_id": cluster_id,
        "fingerprint": json.dumps(fingerprint),
        "created_at": datetime.utcnow().isoformat()
    })

def dynamo_get_baseline(agent_id: str, cluster_id: int):
    db = get_dynamodb_resource()
    if not db:
        return None
    table = db.Table("agent_baseline_baselines")
    try:
        response = table.get_item(Key={"agent_id": agent_id, "cluster_id": cluster_id})
        item = response.get("Item")
        if item:
            return json.loads(item["fingerprint"])
    except ClientError as e:
        logger.error(f"Error getting baseline: {e}")
    return None

def dynamo_get_all_baselines(agent_id: str):
    db = get_dynamodb_resource()
    if not db:
        return {}
    table = db.Table("agent_baseline_baselines")
    try:
        from boto3.dynamodb.conditions import Key
        response = table.query(KeyConditionExpression=Key('agent_id').eq(agent_id))
        items = response.get("Items", [])
        return {int(item["cluster_id"]): json.loads(item["fingerprint"]) for item in items}
    except ClientError as e:
        logger.error(f"Error querying baselines: {e}")
    return {}

def dynamo_save_intent_clusters(agent_id: str, clusters: list):
    db = get_dynamodb_resource()
    if not db:
        return
    table = db.Table("agent_baseline_intent_clusters")
    try:
        from boto3.dynamodb.conditions import Key
        response = table.query(KeyConditionExpression=Key('agent_id').eq(agent_id))
        for item in response.get("Items", []):
            table.delete_item(Key={"agent_id": agent_id, "cluster_id": item["cluster_id"]})
        
        # Save new clusters
        for c in clusters:
            table.put_item(Item={
                "agent_id": agent_id,
                "cluster_id": c["cluster_id"],
                "name": c["name"],
                "keywords": json.dumps(c["keywords"]),
                "size": c["size"]
            })
    except ClientError as e:
        logger.error(f"Error saving intent clusters: {e}")

def dynamo_get_intent_clusters(agent_id: str):
    db = get_dynamodb_resource()
    if not db:
        return []
    table = db.Table("agent_baseline_intent_clusters")
    try:
        from boto3.dynamodb.conditions import Key
        response = table.query(KeyConditionExpression=Key('agent_id').eq(agent_id))
        items = response.get("Items", [])
        for item in items:
            item["cluster_id"] = int(item["cluster_id"])
            item["keywords"] = json.loads(item["keywords"])
            item["size"] = int(item["size"])
        return items
    except ClientError as e:
        logger.error(f"Error getting clusters: {e}")
    return []

def dynamo_save_session(session_id: str, agent_id: str, query: str, cluster_id: int, tool_calls: list, metrics: dict, anomaly_score: float, health_tier: str):
    db = get_dynamodb_resource()
    if not db:
        return
    table = db.Table("agent_baseline_sessions")
    item = {
        "agent_id": agent_id,
        "id": session_id,
        "query": query,
        "cluster_id": cluster_id,
        "tool_calls": json.dumps(tool_calls),
        "metrics": json.dumps(metrics),
        "anomaly_score": str(anomaly_score),
        "health_tier": health_tier,
        "created_at": datetime.utcnow().isoformat()
    }
    table.put_item(Item=item)

def dynamo_get_sessions(agent_id: str, limit: int = 100):
    db = get_dynamodb_resource()
    if not db:
        return []
    table = db.Table("agent_baseline_sessions")
    try:
        from boto3.dynamodb.conditions import Key
        response = table.query(
            KeyConditionExpression=Key('agent_id').eq(agent_id),
            Limit=limit,
            ScanIndexForward=False
        )
        items = response.get("Items", [])
        for item in items:
            item["cluster_id"] = int(item["cluster_id"])
            item["tool_calls"] = json.loads(item["tool_calls"])
            item["metrics"] = json.loads(item["metrics"])
            item["anomaly_score"] = float(item["anomaly_score"])
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[:limit]
    except ClientError as e:
        logger.error(f"Error getting sessions: {e}")
    return []

def dynamo_save_drift_alert(agent_id: str, message: str, score: float):
    db = get_dynamodb_resource()
    if not db:
        return
    table = db.Table("agent_baseline_drift_alerts")
    table.put_item(Item={
        "agent_id": agent_id,
        "created_at": datetime.utcnow().isoformat(),
        "message": message,
        "score": str(score),
        "status": "pending"
    })

def dynamo_get_active_drift_alerts(agent_id: str):
    db = get_dynamodb_resource()
    if not db:
        return []
    table = db.Table("agent_baseline_drift_alerts")
    try:
        from boto3.dynamodb.conditions import Key
        response = table.query(
            KeyConditionExpression=Key('agent_id').eq(agent_id),
            ScanIndexForward=False
        )
        items = response.get("Items", [])
        pending_items = [i for i in items if i["status"] == "pending"]
        for i in pending_items:
            i["score"] = float(i["score"])
        return pending_items
    except ClientError as e:
        logger.error(f"Error getting drift alerts: {e}")
    return []

def dynamo_resolve_drift_alerts(agent_id: str):
    db = get_dynamodb_resource()
    if not db:
        return
    table = db.Table("agent_baseline_drift_alerts")
    try:
        from boto3.dynamodb.conditions import Key
        response = table.query(KeyConditionExpression=Key('agent_id').eq(agent_id))
        items = response.get("Items", [])
        for item in items:
            if item["status"] == "pending":
                table.update_item(
                    Key={"agent_id": agent_id, "created_at": item["created_at"]},
                    UpdateExpression="SET #s = :status",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":status": "refreshed"}
                )
    except ClientError as e:
        logger.error(f"Error resolving drift alerts: {e}")

# Redis Cache

def redis_cache_session(agent_id: str, session: dict):
    r = get_redis_client()
    if not r:
        return
    try:
        key = f"agent_baseline:sessions:{agent_id}"
        r.lpush(key, json.dumps(session))
        r.ltrim(key, 0, 99)
        r.expire(key, 86400)
    except Exception as e:
        logger.error(f"Error caching session: {e}")

def redis_get_sessions(agent_id: str, limit: int = 100) -> list:
    r = get_redis_client()
    if not r:
        return []
    try:
        key = f"agent_baseline:sessions:{agent_id}"
        data = r.lrange(key, 0, limit - 1)
        return [json.loads(s) for s in data]
    except Exception as e:
        logger.error(f"Error reading sessions from Redis: {e}")
    return []

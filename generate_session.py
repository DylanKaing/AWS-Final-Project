import json
import boto3
import uuid
import time

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        # Get class ID from request
        body = json.loads(event['body'])
        class_id = body['classId']
        
        # Generate session data
        session_id = str(uuid.uuid4())
        token = str(uuid.uuid4()).replace('-', '')
        now = int(time.time())
        expires = now + 1800  # 30 minutes
        date = time.strftime('%Y-%m-%d')
        
        # Save to DynamoDB
        table = dynamodb.Table('Sessions')
        table.put_item(Item={
            'sessionId': session_id,
            'classId': class_id,
            'date': date,
            'timestamp': now,
            'qrToken': token,
            'active': True,
            'expiresAt': expires
        })
        
        # Create QR URL
        base_url = "" # GET THIS URL FROM AWS when enabling website hosting on s3
        qr_url = f"{base_url}/attend.html?session={session_id}&token={token}"
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'sessionId': session_id,
                'qrUrl': qr_url,
                'expiresAt': expires
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

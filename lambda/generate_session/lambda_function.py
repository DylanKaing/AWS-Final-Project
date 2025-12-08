import json
import boto3
import uuid
import time
import os

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Generate a new QR code session for a class.
    Triggered when professor clicks "Generate QR Code"
    """
    
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        class_id = body.get('classId')
        
        if not class_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'classId is required'})
            }
        
        # Generate session data
        session_id = str(uuid.uuid4())
        qr_token = str(uuid.uuid4()).replace('-', '')
        current_time = int(time.time())
        expires_at = current_time + 1800  # 30 minutes from now
        date = time.strftime('%Y-%m-%d')
        
        # Save to DynamoDB
        sessions_table = dynamodb.Table('Sessions')
        sessions_table.put_item(Item={
            'sessionId': session_id,
            'classId': class_id,
            'date': date,
            'timestamp': current_time,
            'qrToken': qr_token,
            'active': True,
            'expiresAt': expires_at
        })
        
        # Log CloudWatch metric
        try:
            cloudwatch.put_metric_data(
                Namespace='AttendanceSystem',
                MetricData=[{
                    'MetricName': 'QRCodesGenerated',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': time.time(),
                    'Dimensions': [{
                        'Name': 'ClassID',
                        'Value': class_id
                    }]
                }]
            )
        except Exception as metric_error:
            print(f"CloudWatch metric error: {metric_error}")
            # Don't fail the request if metrics fail
        
        # Get base URL from environment variable or use default
        base_url = os.environ.get('BASE_URL', 'https://d34ooc6u440pf8.cloudfront.net')
        qr_url = f"{base_url}/attendance.html?session={session_id}&token={qr_token}"
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'sessionId': session_id,
                'qrUrl': qr_url,
                'expiresAt': expires_at,
                'classId': class_id
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        
        # Log error metric
        try:
            cloudwatch.put_metric_data(
                Namespace='AttendanceSystem',
                MetricData=[{
                    'MetricName': 'Errors',
                    'Value': 1,
                    'Unit': 'Count'
                }]
            )
        except:
            pass
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

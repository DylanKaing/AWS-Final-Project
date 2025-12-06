import json
import boto3
import time

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Get attendance report for a specific session.
    Triggered when professor views attendance report.
    """
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    try:
        # Get session ID from query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        session_id = query_params.get('sessionId')
        
        if not session_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'sessionId parameter is required'})
            }
        
        # Get DynamoDB tables
        sessions_table = dynamodb.Table('Sessions')
        attendance_table = dynamodb.Table('Attendance')
        
        # Step 1: Get session information
        session_response = sessions_table.get_item(Key={'sessionId': session_id})
        
        if 'Item' not in session_response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Session not found'})
            }
        
        session = session_response['Item']
        
        # Step 2: Query all attendance records for this session
        attendance_response = attendance_table.query(
            IndexName='sessionId-index',
            KeyConditionExpression='sessionId = :sid',
            ExpressionAttributeValues={':sid': session_id}
        )
        
        # Step 3: Build attendance list
        attendance_list = []
        for item in attendance_response.get('Items', []):
            attendance_list.append({
                'studentId': item.get('studentId'),
                'timestamp': int(item.get('timestamp', 0))
            })
        
        # Sort by timestamp (earliest to latest)
        attendance_list.sort(key=lambda x: x['timestamp'])
        
        # Step 4: Build response
        report = {
            'sessionId': session_id,
            'classId': session.get('classId'),
            'date': session.get('date'),
            'sessionCreated': int(session.get('timestamp', 0)),
            'expiresAt': int(session.get('expiresAt', 0)),
            'active': session.get('active', False),
            'totalPresent': len(attendance_list),
            'attendance': attendance_list
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(report)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
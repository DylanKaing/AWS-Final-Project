import json
import boto3

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        # Get session ID from URL
        session_id = event['queryStringParameters']['sessionId']
        
        # Get session info
        sessions_table = dynamodb.Table('Sessions')
        session_response = sessions_table.get_item(Key={'sessionId': session_id})
        
        if 'Item' not in session_response:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Session not found'})
            }
        
        session = session_response['Item']
        
        # Get all attendance records for this session
        attendance_table = dynamodb.Table('Attendance')
        attendance_response = attendance_table.query(
            IndexName='sessionId-index',
            KeyConditionExpression='sessionId = :sid',
            ExpressionAttributeValues={':sid': session_id}
        )
        
        # Build attendance list
        attendance_list = []
        for item in attendance_response['Items']:
            attendance_list.append({
                'studentId': item['studentId'],
                'timestamp': item['timestamp']
            })
        
        # Return report
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'sessionId': session_id,
                'classId': session['classId'],
                'date': session['date'],
                'totalPresent': len(attendance_list),
                'attendance': attendance_list
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

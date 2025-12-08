import json
import boto3
import uuid
import time
import os

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
sns = boto3.client('sns', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Mark a student as present for a class session.
    Triggered when student scans QR code and submits their ID.
    """
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('sessionId')
        qr_token = body.get('qrToken')
        student_id = body.get('studentId')
        
        # Validate input
        if not all([session_id, qr_token, student_id]):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing required fields'})
            }
        
        # Get DynamoDB tables
        sessions_table = dynamodb.Table('Sessions')
        students_table = dynamodb.Table('Students')
        attendance_table = dynamodb.Table('Attendance')
        
        # Step 1: Validate session exists
        session_response = sessions_table.get_item(Key={'sessionId': session_id})
        
        if 'Item' not in session_response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Session not found'})
            }
        
        session = session_response['Item']
        
        # Step 2: Validate token matches
        if session.get('qrToken') != qr_token:
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid QR code token'})
            }
        
        # Step 3: Check if session is still active and not expired
        current_time = int(time.time())
        if current_time > session.get('expiresAt', 0) or not session.get('active', False):
            return {
                'statusCode': 410,
                'headers': headers,
                'body': json.dumps({'error': 'Session has expired'})
            }
        
        # Step 4: Validate student exists in database
        student_response = students_table.get_item(Key={'studentId': student_id})
        
        if 'Item' not in student_response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Student not found in database'})
            }
        
        student = student_response['Item']
        
        # Step 5: Check if student is enrolled in this class
        class_id = session.get('classId')
        enrolled_classes = student.get('enrolledClasses', [])
        
        if class_id not in enrolled_classes:
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({'error': f'Student not enrolled in class {class_id}'})
            }
        
        # Step 6: Check if student already marked present for this session
        existing_attendance = attendance_table.query(
            IndexName='sessionId-index',
            KeyConditionExpression='sessionId = :sid',
            FilterExpression='studentId = :stid',
            ExpressionAttributeValues={
                ':sid': session_id,
                ':stid': student_id
            }
        )
        
        if existing_attendance.get('Count', 0) > 0:
            return {
                'statusCode': 409,
                'headers': headers,
                'body': json.dumps({'message': 'Attendance already marked for this session'})
            }
        
        # Step 7: Mark attendance
        attendance_id = str(uuid.uuid4())
        attendance_table.put_item(Item={
            'attendanceId': attendance_id,
            'sessionId': session_id,
            'studentId': student_id,
            'classId': class_id,
            'timestamp': current_time,
            'status': 'present'
        })
        
        # Step 8: Log CloudWatch metric
        try:
            cloudwatch.put_metric_data(
                Namespace='AttendanceSystem',
                MetricData=[{
                    'MetricName': 'AttendanceMarked',
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': time.time(),
                    'Dimensions': [
                        {'Name': 'ClassID', 'Value': class_id},
                        {'Name': 'SessionID', 'Value': session_id}
                    ]
                }]
            )
        except Exception as metric_error:
            print(f"CloudWatch metric error: {metric_error}")
        
        # Step 9: Send SNS notification (if topic ARN is configured)
        try:
            sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
            if sns_topic_arn:
                sns.publish(
                    TopicArn=sns_topic_arn,
                    Subject=f'Attendance Marked - {class_id}',
                    Message=f'Student {student_id} marked present for {class_id} on {session.get("date")}'
                )
        except Exception as sns_error:
            print(f"SNS notification error: {sns_error}")
            # Don't fail the request if SNS fails
        
        # Return success
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Attendance marked successfully',
                'studentId': student_id,
                'classId': class_id,
                'timestamp': current_time
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
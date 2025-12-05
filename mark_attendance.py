import json
import boto3
import uuid
import time

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        # Get data from request
        body = json.loads(event['body'])
        session_id = body['sessionId']
        token = body['qrToken']
        student_id = body['studentId']
        
        # Check if session exists
        sessions_table = dynamodb.Table('Sessions')
        session_response = sessions_table.get_item(Key={'sessionId': session_id})
        
        if 'Item' not in session_response:
            return error_response(404, 'Session not found')
        
        session = session_response['Item']
        
        # Check token
        if session['qrToken'] != token:
            return error_response(403, 'Invalid token')
        
        # Check if expired
        if time.time() > session['expiresAt'] or not session['active']:
            return error_response(410, 'Session expired')
        
        # Check if student exists
        students_table = dynamodb.Table('Students')
        student_response = students_table.get_item(Key={'studentId': student_id})
        
        if 'Item' not in student_response:
            return error_response(404, 'Student not found in database')
        
        student = student_response['Item']
        
        # Check if enrolled in class
        class_id = session['classId']
        if class_id not in student['enrolledClasses']:
            return error_response(403, 'Student not enrolled in this class')
        
        # Check if already marked present
        attendance_table = dynamodb.Table('Attendance')
        existing = attendance_table.query(
            IndexName='sessionId-index',
            KeyConditionExpression='sessionId = :sid',
            FilterExpression='studentId = :stid',
            ExpressionAttributeValues={
                ':sid': session_id,
                ':stid': student_id
            }
        )
        
        if existing['Count'] > 0:
            return error_response(409, 'Already marked present')
        
        # Mark attendance
        attendance_id = str(uuid.uuid4())
        attendance_table.put_item(Item={
            'attendanceId': attendance_id,
            'sessionId': session_id,
            'studentId': student_id,
            'classId': class_id,
            'timestamp': int(time.time()),
            'status': 'present'
        })
        
        # Success
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Attendance marked successfully',
                'studentId': student_id
            })
        }
        
    except Exception as e:
        return error_response(500, str(e))

def error_response(status, message):
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'error': message})
    }

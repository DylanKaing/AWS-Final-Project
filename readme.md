# QR Code Class Attendance Project

This project is a simple QR-based attendance system that allows teachers to generate a session-specific QR code for their class. Students scan the QR code, enter their student ID, and are automatically marked present. Teachers can view attendance reports using the generated session ID, and they receive email notifications each time a student submits attendance.

---

## Service Justifications

### **CloudFront**
We chose CloudFront over direct S3 access because it:
- Provides **HTTPS/SSL** support for secure handling of student data.
- Caches content globally to reduce latency for teachers and students.
- Offers a clean domain name while allowing the S3 bucket to remain private.

### **CloudWatch**
- Minimal configuration required.
- Automatically captures logs and metrics from Lambda, API Gateway, and DynamoDB.

### **SNS**
- Designed for pub/sub messaging.
- Perfect for **asynchronous attendance email notifications**.

### **DynamoDB**
Chosen over RDS because:
- Automatically scales and uses **pay-per-request** pricing.
- Single-digit millisecond response times for simultaneous student submissions.
- No server maintenance required.
- Flexible NoSQL structure with a GSI for efficient attendance queries.

### **Lambda**
- The system is event-driven and stateless.
- Each operation (generate session, mark attendance, get attendance) is small and short-lived.
- Ideal match for AWS Lambda's serverless execution model.

### **S3**
Selected over EFS/EBS because:
- S3 is highly scalable and cost-efficient.
- Accessible globally—important for student access.
- Designed for static web hosting and object storage.

### **API Gateway**
- Built for managing and deploying APIs.
- Native Lambda integration.
- Requires minimal configuration for routing and HTTP methods.

---

## Setup Instructions

1. Navigate to  
   **https://d34ooc6u440pf8.cloudfront.net/teacher.html**
2. Enter **CS1660** or **CS1550** in the *Generate QR Code* field.
3. Click **Generate QR**.
4. Scan the generated QR code. You will be redirected to:  
   `https://d34ooc6u440pf8.cloudfront.net/attendance.html?session=<sessionId>`
5. Enter a valid student ID:  
   - `S12345` (valid for CS1550 & CS1660)  
   - `S67890` (valid for CS1660 only)
6. Check the teacher's email to confirm attendance notifications.
7. Return to the teacher page to view the attendance report.

---

# Infrastructure Code

Below is the full AWS infrastructure configuration used for this project.

## S3 Bucket
aws s3api create-bucket \
  --bucket "$SITE_BUCKET" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

aws s3api put-bucket-encryption \
  --bucket "$SITE_BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        },
        "BucketKeyEnabled": false
      }
    ]
  }'

aws s3api put-public-access-block \
  --bucket "$SITE_BUCKET" \
  --public-access-block-configuration '{
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }'

## DynamoDB Tables
aws dynamodb create-table \
  --table-name Attendance \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions \
      AttributeName=attendanceId,AttributeType=S \
      AttributeName=sessionId,AttributeType=S \
  --key-schema AttributeName=attendanceId,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "sessionId-index",
      "KeySchema": [
        { "AttributeName": "sessionId", "KeyType": "HASH" }
      ],
      "Projection": { "ProjectionType": "ALL" }
    }
  ]'

aws dynamodb create-table \
  --table-name Students \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions AttributeName=studentId,AttributeType=S \
  --key-schema AttributeName=studentId,KeyType=HASH

aws dynamodb create-table \
  --table-name Classes \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions AttributeName=classId,AttributeType=S \
  --key-schema AttributeName=classId,KeyType=HASH

aws dynamodb create-table \
  --table-name Sessions \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions AttributeName=sessionId,AttributeType=S \
  --key-schema AttributeName=sessionId,KeyType=HASH

## SNS Notifcation Setup
SNS_TOPIC_ARN=$(aws sns create-topic \
  --name attendance-alerts \
  --query TopicArn \
  --output text)
echo "SNS_TOPIC_ARN=$SNS_TOPIC_ARN"

aws sns subscribe \
  --topic-arn "$SNS_TOPIC_ARN" \
  --protocol email \
  --notification-endpoint "teacher@example.com"

We have used dck34@pitt.edu for the teacher email in the demo and all setups

## API Gateway
API_ID=$(aws apigateway create-rest-api \
  --name "attendance-api" \
  --region "$REGION" \
  --api-key-source "HEADER" \
  --endpoint-configuration 'types=REGIONAL' \
  --query id \
  --output text)
echo "API_ID=$API_ID"

## CloudFront Configuration
{
  "CallerReference": "mhw28-final-123456",
  "Comment": "",
  "Enabled": true,
  "PriceClass": "PriceClass_All",
  "DefaultRootObject": "",
  "Origins": [
    {
      "Id": "mhw28-final-project-origin",
      "DomainName": "mhw28-final-project.s3.us-east-1.amazonaws.com",
      "S3OriginConfig": {
        "OriginAccessIdentity": ""
      }
    }
  ],
  "DefaultCacheBehavior": {
    "TargetOriginId": "mhw28-final-project-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": ["GET", "HEAD"],
    "CachedMethods": ["GET", "HEAD"],
    "Compress": true,
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6"
  },
  "Restrictions": {
    "GeoRestriction": { "RestrictionType": "none" }
  },
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": true,
    "MinimumProtocolVersion": "TLSv1",
    "SSLSupportMethod": "vip"
  },
  "HttpVersion": "http2",
  "IsIPV6Enabled": true
}

# Deployment
CF_DIST_JSON=$(aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json)

CF_DOMAIN=$(echo "$CF_DIST_JSON" | jq -r '.Distribution.DomainName')
echo "CF_DOMAIN=$CF_DOMAIN"

# Lambda Functions
CF_DIST_JSON=$(aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json)

CF_DOMAIN=$(echo "$CF_DIST_JSON" | jq -r '.Distribution.DomainName')
echo "CF_DOMAIN=$CF_DOMAIN"

# IAM Policy
aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE_NAME" \
  --policy-name AttendanceLambdaInline \
  --policy-document "{ ... }"

---

## Environment Variables

```bash
REGION="us-east-1"    # change if needed

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

LAMBDA_ROLE_NAME="lambda-image-processing-role"
LAMBDA_ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$LAMBDA_ROLE_NAME"

ARTIFACT_BUCKET="prod-04-2014-tasks"
SITE_BUCKET="mhw28-final-project"
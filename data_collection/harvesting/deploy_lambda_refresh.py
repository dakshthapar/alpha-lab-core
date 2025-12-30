"""
AWS Lambda Deployment Script for Fyers Token Refresh
Automates the deployment of refresh_token.py as an AWS Lambda function.

This script:
1. Creates a deployment package with dependencies
2. Creates/updates Lambda function
3. Sets up EventBridge trigger for daily execution (7:00 AM IST)
4. Configures IAM role with necessary permissions

Requirements:
    - AWS CLI configured (aws configure)
    - boto3 installed
    - IAM permissions to create Lambda functions and EventBridge rules
"""

import os
import sys
import json
import zipfile
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Configuration
LAMBDA_FUNCTION_NAME = 'FyersTokenRefresh'
LAMBDA_ROLE_NAME = 'FyersTokenRefreshRole'
EVENTBRIDGE_RULE_NAME = 'FyersTokenRefreshDaily'
DEFAULT_REGION = 'ap-south-1'
RUNTIME = 'python3.10'
HANDLER = 'refresh_token.lambda_handler'
MEMORY_SIZE = 128  # MB
TIMEOUT = 60  # seconds

# IAM Policy for Lambda
LAMBDA_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:PutParameter"
            ],
            "Resource": "arn:aws:ssm:*:*:parameter/FYERS_*"
        },
        {
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "arn:aws:secretsmanager:*:*:secret:FYERS_PIN*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}

TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

def upload_credentials_from_env(region=DEFAULT_REGION):
    """Read credentials from .env and upload to AWS SSM/Secrets Manager"""
    print("📤 Uploading credentials from .env to AWS...")
    
    # Load .env file
    load_dotenv()
    
    # Get credentials from environment
    client_id = os.getenv('FYERS_CLIENT_ID')
    secret_key = os.getenv('FYERS_SECRET_KEY')
    pin = os.getenv('FYERS_PIN')
    
    # Get tokens from files
    try:
        with open('refresh_token.txt', 'r') as f:
            refresh_token = f.read().strip()
    except FileNotFoundError:
        print("   ⚠️  refresh_token.txt not found, skipping refresh token upload")
        refresh_token = None
    
    try:
        with open('daily_token.txt', 'r') as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        try:
            with open('access_token.txt', 'r') as f:
                access_token = f.read().strip()
        except FileNotFoundError:
            print("   ⚠️  access_token.txt not found, skipping access token upload")
            access_token = None
    
    if not all([client_id, secret_key, pin]):
        print("   ❌ Missing credentials in .env file")
        print("   Required: FYERS_CLIENT_ID, FYERS_SECRET_KEY, FYERS_PIN")
        return False
    
    ssm = boto3.client('ssm', region_name=region)
    secrets = boto3.client('secretsmanager', region_name=region)
    
    # Upload to SSM Parameter Store
    params = [
        ('FYERS_CLIENT_ID', client_id),
        ('FYERS_SECRET_KEY', secret_key),
    ]
    
    if refresh_token:
        params.append(('FYERS_REFRESH_TOKEN', refresh_token))
    
    if access_token:
        params.append(('FYERS_ACCESS_TOKEN', access_token))
    
    for param_name, param_value in params:
        try:
            ssm.put_parameter(
                Name=param_name,
                Value=param_value,
                Type='SecureString',
                Overwrite=True
            )
            print(f"   ✅ Uploaded {param_name} to SSM")
        except Exception as e:
            print(f"   ❌ Failed to upload {param_name}: {e}")
            return False
    
    # Upload PIN to Secrets Manager
    try:
        try:
            secrets.create_secret(
                Name='FYERS_PIN',
                SecretString=pin
            )
            print(f"   ✅ Created FYERS_PIN in Secrets Manager")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                secrets.update_secret(
                    SecretId='FYERS_PIN',
                    SecretString=pin
                )
                print(f"   ✅ Updated FYERS_PIN in Secrets Manager")
            else:
                raise
    except Exception as e:
        print(f"   ❌ Failed to upload PIN: {e}")
        return False
    
    print("✅ All credentials uploaded successfully!")
    return True

def create_deployment_package():
    """Create a ZIP file with Lambda function and dependencies"""
    import subprocess
    import shutil
    
    print("📦 Creating deployment package...")
    
    zip_filename = 'lambda_deployment.zip'
    package_dir = 'lambda_package'
    
    # Clean up old package directory if exists
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir)
    
    # Install requests library to package directory
    print("   📥 Installing requests library...")
    subprocess.run(
        ['pip', 'install', 'requests', '-t', package_dir],
        check=True,
        capture_output=True
    )
    print("   ✅ requests library installed")
    
    # Copy Lambda function to package directory
    shutil.copy('data_collection/harvesting/refresh_token.py', os.path.join(package_dir, 'refresh_token.py'))
    print("   ✅ Added refresh_token.py")
    
    # Create ZIP file from package directory
    shutil.make_archive(zip_filename.replace('.zip', ''), 'zip', package_dir)
    
    # Clean up package directory
    shutil.rmtree(package_dir)
    
    print(f"✅ Deployment package created: {zip_filename}")
    return zip_filename

def create_iam_role(region=DEFAULT_REGION):
    """Create IAM role for Lambda function"""
    iam = boto3.client('iam', region_name=region)
    
    try:
        # Create role
        print(f"🔧 Creating IAM role: {LAMBDA_ROLE_NAME}...")
        response = iam.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
            Description='Role for Fyers token refresh Lambda function'
        )
        role_arn = response['Role']['Arn']
        print(f"   ✅ Role created: {role_arn}")
        
        # Attach inline policy
        print("🔧 Attaching permissions policy...")
        iam.put_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyName='FyersTokenRefreshPolicy',
            PolicyDocument=json.dumps(LAMBDA_POLICY)
        )
        print("   ✅ Policy attached")
        
        return role_arn
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"   ℹ️  Role {LAMBDA_ROLE_NAME} already exists")
            response = iam.get_role(RoleName=LAMBDA_ROLE_NAME)
            return response['Role']['Arn']
        else:
            print(f"❌ Error creating IAM role: {e}")
            sys.exit(1)

def create_lambda_function(zip_filename, role_arn, region=DEFAULT_REGION):
    """Create or update Lambda function"""
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Read deployment package
    with open(zip_filename, 'rb') as f:
        zip_content = f.read()
    
    try:
        # Try to create new function
        print(f"🚀 Creating Lambda function: {LAMBDA_FUNCTION_NAME}...")
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime=RUNTIME,
            Role=role_arn,
            Handler=HANDLER,
            Code={'ZipFile': zip_content},
            Description='Automated Fyers access token refresh',
            Timeout=TIMEOUT,
            MemorySize=MEMORY_SIZE
        )
        function_arn = response['FunctionArn']
        print(f"   ✅ Function created: {function_arn}")
        return function_arn
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            # Function exists, update it
            print(f"   ℹ️  Function exists, updating code...")
            response = lambda_client.update_function_code(
                FunctionName=LAMBDA_FUNCTION_NAME,
                ZipFile=zip_content
            )
            function_arn = response['FunctionArn']
            print(f"   ✅ Function updated: {function_arn}")
            return function_arn
        else:
            print(f"❌ Error creating Lambda function: {e}")
            sys.exit(1)

def create_eventbridge_trigger(function_arn, region=DEFAULT_REGION):
    """Create EventBridge rule to trigger Lambda daily at 7:00 AM IST"""
    events_client = boto3.client('events', region_name=region)
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Cron expression for 7:00 AM IST (1:30 AM UTC)
    # IST = UTC + 5:30
    cron_expression = 'cron(30 1 * * ? *)'
    
    try:
        # Create EventBridge rule
        print(f"⏰ Creating EventBridge rule: {EVENTBRIDGE_RULE_NAME}...")
        events_client.put_rule(
            Name=EVENTBRIDGE_RULE_NAME,
            ScheduleExpression=cron_expression,
            State='ENABLED',
            Description='Trigger Fyers token refresh daily at 7:00 AM IST'
        )
        print(f"   ✅ Rule created with schedule: {cron_expression}")
        
        # Add Lambda permission for EventBridge
        print("🔧 Adding Lambda invoke permission for EventBridge...")
        try:
            lambda_client.add_permission(
                FunctionName=LAMBDA_FUNCTION_NAME,
                StatementId='AllowEventBridgeInvoke',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=f'arn:aws:events:{region}:{boto3.client("sts").get_caller_identity()["Account"]}:rule/{EVENTBRIDGE_RULE_NAME}'
            )
            print("   ✅ Permission added")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceConflictException':
                print("   ℹ️  Permission already exists")
            else:
                raise
        
        # Add Lambda as target
        print("🎯 Setting Lambda as EventBridge target...")
        events_client.put_targets(
            Rule=EVENTBRIDGE_RULE_NAME,
            Targets=[
                {
                    'Id': '1',
                    'Arn': function_arn
                }
            ]
        )
        print("   ✅ Lambda configured as target")
        
    except ClientError as e:
        print(f"❌ Error setting up EventBridge: {e}")
        sys.exit(1)

def main():
    print("="*70)
    print("🚀 AWS Lambda Deployment: Fyers Token Refresh")
    print("="*70)
    
    region = os.environ.get('AWS_REGION', DEFAULT_REGION)
    print(f"\n📍 Region: {region}\n")
    
    # Step 0: Upload credentials from .env to AWS
    print()
    if not upload_credentials_from_env(region):
        print("\n❌ Credential upload failed. Exiting.")
        sys.exit(1)
    
    # Step 1: Create deployment package
    print()
    zip_filename = create_deployment_package()
    
    # Step 2: Create IAM role
    print()
    role_arn = create_iam_role(region)
    
    # Wait for role to propagate
    print("\n⏳ Waiting 10 seconds for IAM role to propagate...")
    import time
    time.sleep(10)
    
    # Step 3: Create/update Lambda function
    print()
    function_arn = create_lambda_function(zip_filename, role_arn, region)
    
    # Step 4: Set up EventBridge trigger
    print()
    create_eventbridge_trigger(function_arn, region)
    
    # Clean up
    print(f"\n🧹 Cleaning up deployment package: {zip_filename}")
    os.remove(zip_filename)
    
    # Final summary
    print("\n" + "="*70)
    print("✅ DEPLOYMENT SUCCESSFUL!")
    print("="*70)
    print(f"\n📋 Summary:")
    print(f"   Function Name: {LAMBDA_FUNCTION_NAME}")
    print(f"   Function ARN: {function_arn}")
    print(f"   Schedule: Daily at 7:00 AM IST (1:30 AM UTC)")
    print(f"   Region: {region}")
    print(f"\n📝 Next Steps:")
    print(f"   1. Store your Fyers PIN in AWS Secrets Manager:")
    print(f"      aws secretsmanager create-secret --name FYERS_PIN --secret-string YOUR_4_DIGIT_PIN")
    print(f"\n   2. Upload your credentials to SSM Parameter Store:")
    print(f"      python data_collection/harvesting/aws_ssm_helper.py set --name FYERS_CLIENT_ID --value <your_client_id>")
    print(f"      python data_collection/harvesting/aws_ssm_helper.py set --name FYERS_SECRET_KEY --value <your_secret_key>")
    print(f"      python data_collection/harvesting/aws_ssm_helper.py set --name FYERS_REFRESH_TOKEN --value <your_refresh_token>")
    print(f"      python data_collection/harvesting/aws_ssm_helper.py set --name FYERS_ACCESS_TOKEN --value <your_access_token>")
    print(f"\n   3. Test the function manually:")
    print(f"      aws lambda invoke --function-name {LAMBDA_FUNCTION_NAME} output.json")
    print(f"\n   4. Check CloudWatch Logs:")
    print(f"      https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group/$252Faws$252Flambda$252F{LAMBDA_FUNCTION_NAME}")
    print("\n" + "="*70)

if __name__ == '__main__':
    main()

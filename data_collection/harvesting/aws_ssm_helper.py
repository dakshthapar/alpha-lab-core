"""
AWS SSM Parameter Store Helper
Command-line tool for managing Fyers credentials in AWS SSM Parameter Store.

Usage:
    # Store a parameter
    python aws_ssm_helper.py set --name FYERS_ACCESS_TOKEN --value <token>
    
    # Retrieve a parameter
    python aws_ssm_helper.py get --name FYERS_ACCESS_TOKEN
    
    # List all Fyers parameters
    python aws_ssm_helper.py list
    
    # Delete a parameter
    python aws_ssm_helper.py delete --name FYERS_ACCESS_TOKEN

Requirements:
    - AWS CLI configured (run: aws configure)
    - boto3 installed (pip install boto3)
    - IAM permissions for SSM Parameter Store
"""

import argparse
import boto3
import sys
from botocore.exceptions import ClientError

DEFAULT_REGION = 'ap-south-1'

def get_ssm_client(region=DEFAULT_REGION):
    """Create SSM client"""
    try:
        return boto3.client('ssm', region_name=region)
    except Exception as e:
        print(f"❌ Error creating SSM client: {e}")
        print("   Make sure AWS CLI is configured: aws configure")
        sys.exit(1)

def set_parameter(name, value, region=DEFAULT_REGION):
    """Store a parameter in SSM Parameter Store (encrypted)"""
    ssm = get_ssm_client(region)
    
    try:
        ssm.put_parameter(
            Name=name,
            Value=value,
            Type='SecureString',
            Overwrite=True,
            Description='Fyers API credential managed by Alpha Lab Core'
        )
        print(f"✅ Parameter '{name}' saved successfully in region {region}")
        print(f"   Type: SecureString (encrypted)")
    except ClientError as e:
        print(f"❌ Error saving parameter: {e}")
        sys.exit(1)

def get_parameter(name, region=DEFAULT_REGION):
    """Retrieve a parameter from SSM Parameter Store"""
    ssm = get_ssm_client(region)
    
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        value = response['Parameter']['Value']
        param_type = response['Parameter']['Type']
        last_modified = response['Parameter']['LastModifiedDate']
        
        print(f"✅ Parameter '{name}' retrieved successfully")
        print(f"   Type: {param_type}")
        print(f"   Last Modified: {last_modified}")
        print(f"\n📌 Value:")
        print("-" * 70)
        print(value)
        print("-" * 70)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound':
            print(f"❌ Parameter '{name}' not found in SSM")
        else:
            print(f"❌ Error retrieving parameter: {e}")
        sys.exit(1)

def list_parameters(region=DEFAULT_REGION):
    """List all Fyers-related parameters in SSM"""
    ssm = get_ssm_client(region)
    
    try:
        # Get all parameters with FYERS prefix
        response = ssm.describe_parameters(
            Filters=[
                {
                    'Key': 'Name',
                    'Values': ['FYERS_']
                }
            ]
        )
        
        parameters = response.get('Parameters', [])
        
        if not parameters:
            print("ℹ️  No Fyers parameters found in SSM Parameter Store")
            print("   Use 'set' command to add parameters")
            return
        
        print(f"✅ Found {len(parameters)} Fyers parameter(s):\n")
        print(f"{'Name':<30} {'Type':<15} {'Last Modified'}")
        print("-" * 70)
        
        for param in parameters:
            name = param['Name']
            param_type = param['Type']
            last_modified = param['LastModifiedDate'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"{name:<30} {param_type:<15} {last_modified}")
            
    except ClientError as e:
        print(f"❌ Error listing parameters: {e}")
        sys.exit(1)

def delete_parameter(name, region=DEFAULT_REGION):
    """Delete a parameter from SSM Parameter Store"""
    ssm = get_ssm_client(region)
    
    # Confirm deletion
    confirm = input(f"⚠️  Are you sure you want to delete '{name}'? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Deletion cancelled")
        return
    
    try:
        ssm.delete_parameter(Name=name)
        print(f"✅ Parameter '{name}' deleted successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound':
            print(f"❌ Parameter '{name}' not found")
        else:
            print(f"❌ Error deleting parameter: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='AWS SSM Parameter Store Helper for Fyers Credentials',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Store access token
  python aws_ssm_helper.py set --name FYERS_ACCESS_TOKEN --value eyJ0eXAi...
  
  # Store refresh token
  python aws_ssm_helper.py set --name FYERS_REFRESH_TOKEN --value dGhpcyBpc...
  
  # Retrieve token
  python aws_ssm_helper.py get --name FYERS_ACCESS_TOKEN
  
  # List all parameters
  python aws_ssm_helper.py list
  
  # Delete parameter
  python aws_ssm_helper.py delete --name FYERS_ACCESS_TOKEN
        '''
    )
    
    parser.add_argument('--region', default=DEFAULT_REGION, 
                        help=f'AWS region (default: {DEFAULT_REGION})')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Set command
    set_parser = subparsers.add_parser('set', help='Store a parameter')
    set_parser.add_argument('--name', required=True, help='Parameter name')
    set_parser.add_argument('--value', required=True, help='Parameter value')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Retrieve a parameter')
    get_parser.add_argument('--name', required=True, help='Parameter name')
    
    # List command
    subparsers.add_parser('list', help='List all Fyers parameters')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a parameter')
    delete_parser.add_argument('--name', required=True, help='Parameter name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == 'set':
        set_parameter(args.name, args.value, args.region)
    elif args.command == 'get':
        get_parameter(args.name, args.region)
    elif args.command == 'list':
        list_parameters(args.region)
    elif args.command == 'delete':
        delete_parameter(args.name, args.region)

if __name__ == '__main__':
    main()

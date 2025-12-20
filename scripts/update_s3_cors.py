#!/usr/bin/env python3
"""
Update S3 bucket CORS configuration to allow thumbnail generation from localhost
"""
import boto3
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

def update_cors():
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-2')
    )

    bucket_name = os.getenv('AWS_S3_BUCKET', 'taylorswiftnyu')

    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'HEAD'],
            'AllowedOrigins': [
                'http://localhost:3000',
                'http://localhost:3001',
                'http://localhost:3002',
                'https://phraze.so',
                'https://*.phraze.so'
            ],
            'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type'],
            'MaxAgeSeconds': 3600
        }]
    }

    try:
        s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
        print(f"Successfully updated CORS configuration for bucket: {bucket_name}")

        # Verify the configuration
        response = s3_client.get_bucket_cors(Bucket=bucket_name)
        print("Current CORS configuration:")
        for rule in response['CORSRules']:
            print(f"  AllowedOrigins: {rule['AllowedOrigins']}")
            print(f"  AllowedMethods: {rule['AllowedMethods']}")
            print(f"  AllowedHeaders: {rule['AllowedHeaders']}")
    except Exception as e:
        print(f"Error updating CORS: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_cors()

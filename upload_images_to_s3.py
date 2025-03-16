#!/usr/bin/env python3
"""
Script to upload all images in the static/images directory to S3
"""
import os
import sys
import time
from dotenv import load_dotenv
from utils.s3_utils import upload_directory_to_s3

# Load environment variables
load_dotenv()

# Check for required environment variables
required_env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET']
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these in your .env file or environment")
    sys.exit(1)

# Get bucket name
bucket_name = os.environ['AWS_S3_BUCKET']

# Directory to upload
image_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images')

if not os.path.exists(image_directory):
    print(f"Error: Image directory not found: {image_directory}")
    sys.exit(1)

print(f"Starting upload of images from {image_directory} to S3 bucket {bucket_name}")
print("This may take a while for many or large images...")

# Time the upload
start_time = time.time()

# Upload all images to S3 with public-read access
results = upload_directory_to_s3(
    image_directory, 
    bucket_name, 
    prefix="images", 
    make_public=True
)

end_time = time.time()
elapsed_time = end_time - start_time

# Print results
print(f"\nUpload completed in {elapsed_time:.2f} seconds")
print(f"Successfully uploaded {len(results['success'])} files")

if results['failed']:
    print(f"Failed to upload {len(results['failed'])} files:")
    for file in results['failed']:
        print(f"  - {file}")

# Print sample URLs
if results['success']:
    region = os.environ.get('AWS_REGION', 'us-east-1')
    print("\nSample image URLs:")
    for i, key in enumerate(results['success'][:3]):  # Show first 3 examples
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
        print(f"  {i+1}. {url}")

print("\nDone!")
import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_s3_client():
    """
    Create and return an S3 client using environment variables.
    
    Returns:
        boto3.client: The S3 client or None if creation fails
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        return s3_client
    except Exception as e:
        logger.error(f"Error creating S3 client: {str(e)}")
        return None

def s3_image_url(bucket_name, image_key):
    """
    Generate a URL for an S3 image.
    
    Args:
        bucket_name (str): S3 bucket name
        image_key (str): Image key/path in the bucket
        
    Returns:
        str: The URL for the S3 image
    """
    # Using the standard S3 path format
    region = os.environ.get('AWS_REGION', 'us-east-1')
    return f"https://{bucket_name}.s3.{region}.amazonaws.com/{image_key}"

def upload_file_to_s3(file_path, bucket_name, object_name=None, make_public=False):
    """
    Upload a file to an S3 bucket
    
    Args:
        file_path (str): Path to the file to upload
        bucket_name (str): Bucket to upload to
        object_name (str): S3 object name. If not specified, file_path's basename is used
        make_public (bool): Whether to make the uploaded file publicly accessible
        
    Returns:
        bool: True if file was uploaded, False otherwise
    """
    # If object_name wasn't specified, use file_path's basename
    if object_name is None:
        object_name = os.path.basename(file_path)
    
    # Get S3 client
    s3_client = get_s3_client()
    if not s3_client:
        return False
    
    try:
        extra_args = {}
        if make_public:
            extra_args['ACL'] = 'public-read'
            
        # Upload the file
        s3_client.upload_file(
            file_path, 
            bucket_name, 
            object_name,
            ExtraArgs=extra_args
        )
        logger.info(f"Successfully uploaded {file_path} to {bucket_name}/{object_name}")
        return True
    except FileNotFoundError:
        logger.error(f"The file {file_path} was not found")
        return False
    except NoCredentialsError:
        logger.error("Credentials not available")
        return False
    except ClientError as e:
        logger.error(f"S3 client error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {str(e)}")
        return False

def list_bucket_contents(bucket_name, prefix=""):
    """
    List contents of an S3 bucket with an optional prefix
    
    Args:
        bucket_name (str): Name of the bucket
        prefix (str): Optional prefix to filter results
        
    Returns:
        list: List of objects in the bucket or None if failed
    """
    s3_client = get_s3_client()
    if not s3_client:
        return None
    
    try:
        # List objects in the bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        if 'Contents' in response:
            return response['Contents']
        else:
            logger.info(f"No objects found in {bucket_name} with prefix '{prefix}'")
            return []
    except ClientError as e:
        logger.error(f"Error listing bucket contents: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error listing bucket contents: {str(e)}")
        return None

def upload_directory_to_s3(directory_path, bucket_name, prefix="", make_public=False):
    """
    Upload an entire directory to an S3 bucket
    
    Args:
        directory_path (str): Path to the directory to upload
        bucket_name (str): Name of the S3 bucket
        prefix (str): Prefix to add to object keys
        make_public (bool): Whether to make uploaded files publicly accessible
        
    Returns:
        dict: Dictionary with 'success' and 'failed' lists
    """
    results = {'success': [], 'failed': []}
    
    # Check if the directory exists
    if not os.path.isdir(directory_path):
        logger.error(f"Directory {directory_path} does not exist")
        return results
    
    # Walk through the directory
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Create the S3 object key
            relative_path = os.path.relpath(file_path, directory_path)
            s3_key = os.path.join(prefix, relative_path).replace("\\", "/")
            
            # Upload the file
            if upload_file_to_s3(file_path, bucket_name, s3_key, make_public):
                results['success'].append(s3_key)
            else:
                results['failed'].append(file_path)
    
    return results
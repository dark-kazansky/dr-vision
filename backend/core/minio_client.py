import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from settings import settings

logger = logging.getLogger(__name__)

class MinioClient:
    def __init__(self):
        self.endpoint = settings.minio_endpoint
        self.access_key = settings.minio_access_key
        self.secret_key = settings.minio_secret_key
        self.bucket_name = settings.minio_bucket_name
        
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            # MinIO doesn't use standard AWS regions, but boto3 might complain if absent
            region_name="us-east-1"
        )
        self.ensure_bucket_exists()

    def ensure_bucket_exists(self) -> None:
        """Create the configured bucket if it doesn't already exist."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.info(f"Bucket {self.bucket_name} not found. Creating it.")
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                except Exception as ex:
                    logger.error(f"Failed to create bucket: {ex}")
            else:
                logger.error(f"Error checking bucket {self.bucket_name}: {e}")

    def upload_file(self, local_file_path: str, object_name: str) -> bool:
        """Upload a file from local disk to MinIO."""
        try:
            self.s3_client.upload_file(local_file_path, self.bucket_name, object_name)
            logger.info(f"Successfully uploaded {local_file_path} to {self.bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            return False

    def upload_bytes(self, data: bytes, object_name: str, content_type: str = "application/octet-stream") -> bool:
        """Upload raw bytes to MinIO."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=data,
                ContentType=content_type,
            )
            logger.info(f"Successfully uploaded bytes to {self.bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload bytes to MinIO: {e}")
            return False

    def delete_object(self, object_name: str) -> bool:
        """Delete an object from MinIO."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"Deleted {self.bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete object from MinIO: {e}")
            return False

    def generate_presigned_url(self, object_name: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for downloading an object."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return ""

    def upload_json(self, dict_data: Dict[str, Any], object_name: str) -> bool:
        """Upload a JSON dictionary to MinIO."""
        try:
            json_str = json.dumps(dict_data, ensure_ascii=False, indent=2)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=json_str.encode("utf-8"),
                ContentType="application/json"
            )
            logger.info(f"Successfully uploaded JSON to {self.bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload JSON to MinIO: {e}")
            return False

# Global singleton
minio_client = MinioClient()

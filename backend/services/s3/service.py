"""
S3 service for uploading videos and managing file storage
Based on zhaoli_processor.py logic
"""

import boto3
import os
import logging
from typing import Optional, Dict
from botocore.exceptions import ClientError, NoCredentialsError

from backend.config import settings
from backend.services.s3.helpers import (
    ensure_unique_key,
    validate_file_exists,
    create_s3_key_path
)
from backend.services.s3.audio_uploader import AudioUploader

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 uploads and downloads"""

    def __init__(self) -> None:
        """Initialize S3 client with credentials from settings"""
        try:
            # Get credentials and strip any whitespace/newlines
            aws_key = (settings.aws_access_key_id or "").strip()
            aws_secret = (settings.aws_secret_access_key or "").strip()
            region = (settings.aws_region or "us-east-1").strip()
            bucket = (settings.aws_s3_bucket or "your-s3-bucket-name").strip()

            # Log credential info for debugging (safely)
            logger.info(f"AWS credentials check:")
            logger.info(f"  - Access Key ID: {aws_key[:4]}...{aws_key[-4:] if len(aws_key) > 8 else 'SHORT'} (len={len(aws_key)})")
            logger.info(f"  - Secret Key: {'SET' if aws_secret else 'NOT SET'} (len={len(aws_secret)})")
            logger.info(f"  - Region: {region}")
            logger.info(f"  - Bucket: {bucket}")

            # Validate credentials are present
            if not aws_key or not aws_secret:
                logger.error("AWS credentials not configured properly")
                logger.error(f"AWS_ACCESS_KEY_ID set: {bool(aws_key)}")
                logger.error(f"AWS_SECRET_ACCESS_KEY set: {bool(aws_secret)}")

            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=region
            )
            self.bucket_name = bucket
            self.audio_uploader = AudioUploader(self)
            logger.info(f"S3 service initialized with bucket: {self.bucket_name}")
        except NoCredentialsError as e:
            logger.error("AWS credentials not found")
            raise e
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise e

    def upload_video_and_get_url(
        self,
        local_file_path: str,
        s3_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload a video file to S3 and return its public URL.

        Args:
            local_file_path: Path to the local video file
            s3_key: Optional custom key for S3 storage. If not provided, uses filename

        Returns:
            Public URL of the uploaded video, or None if upload failed
        """
        try:
            if not validate_file_exists(local_file_path):
                logger.error(f"Local file not found: {local_file_path}")
                return None

            if not s3_key:
                s3_key = os.path.basename(local_file_path)

            s3_key = ensure_unique_key(s3_key, self.file_exists)

            logger.info(
                f"Uploading {local_file_path} to S3 bucket "
                f"{self.bucket_name} with key {s3_key}"
            )

            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ACL': 'public-read'}
            )

            public_url = self.get_public_url(s3_key)

            logger.info(f"Video uploaded successfully. Public URL: {public_url}")
            return public_url

        except ClientError as e:
            logger.error(f"AWS S3 error during upload: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            return None

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download a file from S3 to local path.

        Args:
            s3_key: S3 object key
            local_path: Local path to save the file

        Returns:
            True if successful, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            logger.info(f"Downloading {s3_key} from S3 to {local_path}")

            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )

            logger.info(f"Successfully downloaded file to {local_path}")
            return True

        except ClientError as e:
            logger.error(f"AWS S3 error during download: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 download: {e}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_key: S3 object key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting {s3_key} from S3 bucket {self.bucket_name}")

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            logger.info(f"Successfully deleted {s3_key} from S3")
            return True

        except ClientError as e:
            logger.error(f"AWS S3 error during deletion: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 deletion: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: S3 object key to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_public_url(self, s3_key: str) -> str:
        """
        Get the public URL for an S3 object.

        Args:
            s3_key: S3 object key

        Returns:
            Public URL string
        """
        return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"

    def get_presigned_url(self, s3_key: str, expiration: int = 7200) -> str:
        """
        Generate a presigned URL for temporary public access.

        This works even if the bucket blocks public access.
        Useful for external services like Sync.so that need temporary access.

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 2 hours)

        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {s3_key} (expires in {expiration}s)")
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            # Fallback to public URL
            return self.get_public_url(s3_key)

    def test_connection(self) -> bool:
        """
        Test S3 connection and permissions.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=1
            )
            logger.info("S3 connection test successful")
            return True
        except ClientError as e:
            logger.error(f"S3 connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 connection test: {e}")
            return False

    def upload_multiple_audio_files(
        self,
        audio_file_paths: list,
        user_id: str,
        job_id: str
    ) -> Dict[str, str]:
        """
        Upload multiple audio files to S3 for Pro Video Editor segments

        Args:
            audio_file_paths: List of local audio file paths
            user_id: User ID for S3 path organization
            job_id: Job ID for S3 path organization

        Returns:
            Dict mapping refId -> S3 URL for each audio file
            Example: {"audio-uuid-1": "https://...", "audio-uuid-2": "https://..."}
        """
        return self.audio_uploader.upload_multiple_files(
            audio_file_paths,
            user_id,
            job_id
        )

    def upload_multiple_audio_files_with_refids(
        self,
        audio_refid_map: Dict[str, str],
        user_id: str,
        job_id: str
    ) -> Dict[str, str]:
        """
        Upload multiple audio files to S3 with preserved refIds from frontend

        Args:
            audio_refid_map: Dict mapping audio file path -> refId
                Example: {"/tmp/audio_0.mp3": "audio-1760661529869-tdshi62pu"}
            user_id: User ID for S3 path organization
            job_id: Job ID for S3 path organization

        Returns:
            Dict mapping refId -> S3 URL for each audio file
            Example: {"audio-1760661529869-tdshi62pu": "https://..."}
        """
        return self.audio_uploader.upload_files_with_refids(
            audio_refid_map,
            user_id,
            job_id
        )


# Global S3 service instance
s3_service = S3Service()

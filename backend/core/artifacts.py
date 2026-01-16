"""
Artifact Service - Centralized handling of generated artifacts (plots, reports, etc.)

This module provides a clean interface for storing and retrieving artifacts,
with consistent behavior for both S3 and local storage backends.
"""

import os
import uuid
import mimetypes
from typing import Generator, Optional
from io import BytesIO

from core.logger import logger
from core.config import settings


class ArtifactService:
    """
    Centralized service for artifact storage and retrieval.
    
    Key features:
    - Conversation-scoped storage keys to prevent collisions
    - Direct streaming without temp file intermediaries
    - Consistent API for S3 and local storage
    """
    
    def __init__(self):
        self.local_artifact_dir = "uploads/artifacts"
        self.bucket_name = settings.AWS_BUCKET_NAME
        
        # Check if S3 is configured
        if self.bucket_name and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            import boto3
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.mode = "s3"
            logger.info("ArtifactService configured with S3")
        else:
            self.mode = "local"
            os.makedirs(self.local_artifact_dir, exist_ok=True)
            logger.info(f"ArtifactService configured with local storage: {self.local_artifact_dir}")
    
    def save_artifact(self, file_path: str, conversation_id: str) -> str:
        """
        Save an artifact to permanent storage with conversation-scoped naming.
        
        Args:
            file_path: Local path to the artifact file
            conversation_id: ID of the conversation this artifact belongs to
            
        Returns:
            Storage key that can be used to retrieve the artifact
        """
        filename = os.path.basename(file_path)
        unique_id = uuid.uuid4().hex[:8]
        key = f"artifacts/{conversation_id}/{unique_id}_{filename}"
        
        # Get file size for logging
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        logger.info(f"[ARTIFACT LIFECYCLE] ArtifactService.save_artifact called")
        logger.info(f"[ARTIFACT LIFECYCLE] Input: file_path={file_path}, conversation_id={conversation_id}")
        logger.info(f"[ARTIFACT LIFECYCLE] File size: {file_size} bytes")
        logger.info(f"[ARTIFACT LIFECYCLE] Storage mode: {self.mode}")
        logger.info(f"[ARTIFACT LIFECYCLE] Generated storage key: {key}")
        
        if self.mode == "s3":
            try:
                from boto3.s3.transfer import TransferConfig
                
                # Configure for large file uploads
                # Use multipart for files > 5MB, with reasonable timeouts
                transfer_config = TransferConfig(
                    multipart_threshold=5 * 1024 * 1024,  # 5MB
                    max_concurrency=10,
                    multipart_chunksize=5 * 1024 * 1024,  # 5MB chunks
                    use_threads=True
                )
                
                # Upload with config
                self.s3_client.upload_file(
                    file_path, 
                    self.bucket_name, 
                    key,
                    Config=transfer_config
                )
                
                # Verify upload succeeded by checking if object exists
                try:
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                    logger.info(f"Uploaded artifact to S3: {key} (verified)")
                except Exception as verify_err:
                    logger.error(f"Upload verification failed for {key}: {verify_err}")
                    raise RuntimeError(f"Upload verification failed: {verify_err}")
                
                return key
            except Exception as e:
                logger.error(f"Failed to upload artifact to S3: {e}")
                raise
        else:
            # Local storage
            dest_dir = os.path.join(self.local_artifact_dir, conversation_id)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, f"{unique_id}_{filename}")
            
            import shutil
            shutil.copy2(file_path, dest_path)
            logger.info(f"Saved artifact locally: {dest_path}")
            return key  # Return consistent key format regardless of storage mode
    
    def get_artifact_url(self, key: str) -> str:
        """
        Get the URL to access an artifact.
        
        Args:
            key: Storage key returned by save_artifact
            
        Returns:
            URL path for API access (e.g., /api/artifacts/...)
        """
        url = f"/api/artifacts/{key}"
        logger.info(f"[ARTIFACT LIFECYCLE] Generated artifact URL: {url}")
        return url
    
    def stream_artifact(self, key: str) -> Generator[bytes, None, None]:
        """
        Stream artifact content directly from storage.
        
        Args:
            key: Storage key
            
        Yields:
            Chunks of file content
        """
        logger.info(f"[ARTIFACT LIFECYCLE] stream_artifact called with key: {key}")
        chunk_size = 8192
        total_bytes = 0
        
        if self.mode == "s3":
            try:
                logger.info(f"[ARTIFACT LIFECYCLE] Fetching from S3 bucket={self.bucket_name}")
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                body = response['Body']
                content_length = response.get('ContentLength', 'unknown')
                logger.info(f"[ARTIFACT LIFECYCLE] S3 object retrieved, ContentLength={content_length}")
                while True:
                    chunk = body.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    yield chunk
                logger.info(f"[ARTIFACT LIFECYCLE] Finished streaming from S3, total bytes={total_bytes}")
            except Exception as e:
                logger.error(f"[ARTIFACT LIFECYCLE] Failed to stream artifact from S3: {e}")
                raise FileNotFoundError(f"Artifact not found: {key}")
        else:
            # Local storage - map key back to file path
            # Key format: artifacts/{conversation_id}/{uuid}_{filename}
            parts = key.split('/', 2)  # ['artifacts', 'conv_id', 'uuid_filename']
            if len(parts) == 3:
                local_path = os.path.join(self.local_artifact_dir, parts[1], parts[2])
            else:
                logger.error(f"[ARTIFACT LIFECYCLE] Invalid artifact key format: {key}")
                raise FileNotFoundError(f"Invalid artifact key: {key}")
            
            logger.info(f"[ARTIFACT LIFECYCLE] Local storage path: {local_path}")
            
            if not os.path.exists(local_path):
                logger.error(f"[ARTIFACT LIFECYCLE] Local file does not exist: {local_path}")
                raise FileNotFoundError(f"Artifact not found: {key}")
            
            file_size = os.path.getsize(local_path)
            logger.info(f"[ARTIFACT LIFECYCLE] Local file exists, size={file_size} bytes")
            
            with open(local_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    yield chunk
            logger.info(f"[ARTIFACT LIFECYCLE] Finished streaming from local, total bytes={total_bytes}")
    
    def get_artifact_bytes(self, key: str) -> bytes:
        """
        Get full artifact content as bytes.
        Useful for reading JSON reports into memory.
        
        Args:
            key: Storage key
            
        Returns:
            Full file content as bytes
        """
        chunks = []
        for chunk in self.stream_artifact(key):
            chunks.append(chunk)
        return b''.join(chunks)
    
    def get_media_type(self, key: str) -> str:
        """
        Determine the media type for an artifact based on its filename.
        
        Args:
            key: Storage key
            
        Returns:
            MIME type string
        """
        filename = key.split('/')[-1]
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            return mime_type
        
        # Fallback for common types
        if filename.endswith('.png'):
            return 'image/png'
        elif filename.endswith('.html'):
            return 'text/html'
        elif filename.endswith('.json'):
            return 'application/json'
        elif filename.endswith('.csv'):
            return 'text/csv'
        else:
            return 'application/octet-stream'


# Singleton instance
artifact_service = ArtifactService()

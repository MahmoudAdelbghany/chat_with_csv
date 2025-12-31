import boto3
import os
from botocore.exceptions import ClientError
from fastapi import HTTPException
from core.logger import logger
from core.config import settings
import shutil

class StorageService:
    def __init__(self):
        self.bucket_name = settings.AWS_BUCKET_NAME
        self.local_upload_dir = "uploads"
        
        # Check if S3 is configured
        if self.bucket_name and settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.mode = "s3"
            logger.info(f"Storage configured with S3 bucket: {self.bucket_name}")
        else:
            self.mode = "local"
            os.makedirs(self.local_upload_dir, exist_ok=True)
            logger.info("Storage configured with Local Filesystem")

    def upload_file(self, file_obj, filename: str) -> str:
        """
        Uploads a file to storage. Returns the stored path/key.
        """
        if self.mode == "s3":
            try:
                # Reset file pointer just in case
                file_obj.seek(0)
                self.s3_client.upload_fileobj(file_obj, self.bucket_name, filename)
                return filename
            except ClientError as e:
                logger.error(f"S3 Upload Error: {e}")
                raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        else:
            # Local fallback
            file_path = os.path.join(self.local_upload_dir, filename)
            with open(file_path, "wb") as buffer:
                file_obj.seek(0)
                shutil.copyfileobj(file_obj, buffer)
            return file_path

    def download_file(self, file_path: str, destination_path: str):
        """
        Downloads a file from storage to a local destination.
        """
        if self.mode == "s3":
            try:
                # file_path in DB is just the key for S3
                self.s3_client.download_file(self.bucket_name, file_path, destination_path)
            except ClientError as e:
                logger.error(f"S3 Download Error: {e}")
                if e.response['Error']['Code'] == "404":
                    raise FileNotFoundError(f"File {file_path} not found in storage")
                raise e
        else:
            # Local fallback
            # If the stored path is relative or absolute, handle it
            # In local mode, file_path stored in DB is likely "uploads/filename.csv"
            # But if we switched modes, we might have issues. 
            # Assuming file_path is what was returned by upload_file.
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File {file_path} not found locally")
            
            if file_path != destination_path:
                shutil.copy2(file_path, destination_path)

storage = StorageService()

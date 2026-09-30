import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Storage:

    def __init__(self):

        if not settings.aws_s3_bucket:
            raise ValueError(
                "AWS_S3_BUCKET is not configured"
            )

        self.bucket = (
            settings.aws_s3_bucket
        )

        self.client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=(
                settings.aws_access_key_id
            ),
            aws_secret_access_key=(
                settings.aws_secret_access_key
            ),
        )

    def save_upload(
        self,
        file_obj,
        destination_key: str
    ) -> tuple[str, int]:

        file_obj.seek(0)

        self.client.upload_fileobj(
            file_obj,
            self.bucket,
            destination_key
        )

        metadata = self.client.head_object(
            Bucket=self.bucket,
            Key=destination_key
        )

        return (
            destination_key,
            metadata.get("ContentLength", 0)
        )

    def exists(
        self,
        key: str
    ) -> bool:

        try:

            self.client.head_object(
                Bucket=self.bucket,
                Key=key
            )

            return True

        except ClientError:

            return False

    def delete(
        self,
        key: str
    ) -> None:

        self.client.delete_object(
            Bucket=self.bucket,
            Key=key
        )

    def copy(
        self,
        source_key: str,
        destination_key: str
    ) -> tuple[str, int]:

        self.client.copy_object(
            Bucket=self.bucket,

            CopySource={
                "Bucket": self.bucket,
                "Key": source_key,
            },

            Key=destination_key,
        )

        metadata = self.client.head_object(
            Bucket=self.bucket,
            Key=destination_key
        )

        return (
            destination_key,
            metadata.get("ContentLength", 0)
        )

    def download(
        self,
        key: str
    ):

        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key
        )

        return response["Body"]
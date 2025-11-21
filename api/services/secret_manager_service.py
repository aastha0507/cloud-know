from google.cloud import secretmanager
import os

class SecretManagerService:
    def __init__(self):
        self.client = secretmanager.SecretManagerServiceClient()

        # Works locally + Cloud Run + Cloud Shell
        self.project_id = (
            os.getenv("GCP_PROJECT_ID") or
            os.getenv("PROJECT_ID") or
            os.getenv("GOOGLE_CLOUD_PROJECT")
        )

        if not self.project_id:
            raise ValueError("No GCP project ID found in environment variables.")

    def get_secret(self, secret_name: str):
        secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        response = self.client.access_secret_version(request={"name": secret_path})
        return response.payload.data.decode("utf-8")

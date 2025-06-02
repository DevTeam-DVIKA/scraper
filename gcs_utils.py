# gcs_utils.py

from google.cloud import storage

# ── CONFIGURE YOUR BUCKET HERE ───────────────────────────────────────────────
GCS_BUCKET_NAME = "legal-data-bucket" 

# Initialize client and bucket once
_client = storage.Client()
_bucket = _client.bucket(GCS_BUCKET_NAME)

def upload_to_gcs(local_path: str, dest_path: str) -> str:
    """
    Upload `local_path` to gs://<GCS_BUCKET_NAME>/<dest_path>
    Returns the public URL of the uploaded object.
    """
    blob = _bucket.blob(dest_path)
    blob.upload_from_filename(local_path)
    # If you want the object to be publicly readable, uncomment next line:
    # blob.make_public()
    return blob.public_url

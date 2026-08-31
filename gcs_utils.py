# gcs_utils.py
import json
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account

def test_gcs_connection():
    """Test Google Cloud Storage connection"""
    try:
        credentials_json = st.secrets.get("GCS_CREDENTIALS")
        if not credentials_json:
            return "❌ GCS_CREDENTIALS not found"
        
        if isinstance(credentials_json, str):
            creds_dict = json.loads(credentials_json)
        else:
            creds_dict = credentials_json
        
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = storage.Client(credentials=credentials)
        
        bucket_name = st.secrets.get("GCS_BUCKET_NAME")
        bucket = client.bucket(bucket_name)
        
        test_blob = bucket.blob("test/test_connection.txt")
        test_blob.upload_from_string("✅ GCS connection successful!")
        test_blob.delete()
        
        return f"✅ GCS connected! Bucket: {bucket_name}"
        
    except Exception as e:
        return f"❌ GCS error: {str(e)}"
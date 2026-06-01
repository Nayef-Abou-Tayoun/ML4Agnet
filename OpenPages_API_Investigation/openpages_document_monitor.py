#!/usr/bin/env python3
"""
OpenPages Document Monitor
Monitors a specific process for new documents and automatically downloads them
and uploads them to IBM Cloud Object Storage.
"""

import requests
import time
import os
import json
from datetime import datetime
from requests.auth import HTTPBasicAuth
import ibm_boto3
from ibm_botocore.client import Config
from flask import Flask, jsonify
import threading

# ============================================================================
# CONFIGURATION - Using environment variables
# ============================================================================

# OpenPages Server Configuration
OPENPAGES_SERVER = os.getenv("OPENPAGES_SERVER", "http://useast.services.cloud.techzone.ibm.com:22816")
USERNAME = os.getenv("OPENPAGES_USERNAME", "OpenPagesAdministrator")
PASSWORD = os.getenv("OPENPAGES_PASSWORD", "OpenPagesAdministrator")

# Process to Monitor
PROCESS_ID = os.getenv("PROCESS_ID", "211034")
PROCESS_NAME = os.getenv("PROCESS_NAME", "ABC Financial Institution_PROC_00203")

# Monitoring Configuration
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

# IBM Cloud Object Storage Configuration
COS_API_KEY = os.getenv("COS_API_KEY", "5fiEq8dYgopufWDJIlBHojvmfw34TBf5G_w12FhWVctT")
COS_INSTANCE_CRN = os.getenv("COS_INSTANCE_CRN", "crn:v1:bluemix:public:cloud-object-storage:global:a/1d334f6f5c4a402389b1001f50d6565d:67317f29-f4cd-473a-8531-9593bb41c7c5::")
COS_ENDPOINT = os.getenv("COS_ENDPOINT", "https://s3.us-south.cloud-object-storage.appdomain.cloud")
COS_BUCKET_NAME = os.getenv("COS_BUCKET_NAME", "openpages-objects")

# ============================================================================
# DO NOT MODIFY BELOW THIS LINE
# ============================================================================

class OpenPagesDocumentMonitor:
    def __init__(self, server, username, password, process_id, check_interval,
                 cos_api_key=None, cos_instance_crn=None, cos_endpoint=None, cos_bucket=None):
        self.server = server
        self.auth = HTTPBasicAuth(username, password)
        self.process_id = process_id
        self.check_interval = check_interval
        self.known_documents = set()
        
        # IBM COS Configuration
        self.cos_enabled = all([cos_api_key, cos_instance_crn, cos_endpoint, cos_bucket])
        self.cos_bucket = cos_bucket
        
        if self.cos_enabled:
            # Initialize IBM COS client
            self.cos_client = ibm_boto3.client(
                's3',
                ibm_api_key_id=cos_api_key,
                ibm_service_instance_id=cos_instance_crn,
                config=Config(signature_version='oauth'),
                endpoint_url=cos_endpoint
            )
            print(f"✓ IBM Cloud Object Storage client initialized")
            print(f"✓ Target bucket: {cos_bucket}")
            
            # Verify bucket exists and is accessible
            if self.verify_bucket_access():
                print(f"✓ Bucket verified and accessible")
                print(f"✓ Documents will be uploaded directly to COS (no local storage)")
            else:
                print(f"✗ ERROR: Cannot access bucket '{cos_bucket}'")
                print(f"✗ Please check bucket name and permissions")
                self.cos_enabled = False
        else:
            self.cos_client = None
            print(f"⚠ WARNING: IBM Cloud Object Storage not configured!")
            print(f"⚠ Documents will NOT be saved anywhere!")
    
    def verify_bucket_access(self):
        """Verify that the bucket exists and is accessible"""
        try:
            # Try to upload a test file to verify write access
            test_key = "test/connection_test.txt"
            test_content = b"Connection test"
            self.cos_client.put_object(
                Bucket=self.cos_bucket,
                Key=test_key,
                Body=test_content
            )
            # Try to delete the test file
            try:
                self.cos_client.delete_object(Bucket=self.cos_bucket, Key=test_key)
            except:
                pass  # Ignore delete errors
            return True
        except Exception as e:
            print(f"   Error details: {str(e)}")
            print(f"   Note: Writer role may not have sufficient permissions")
            print(f"   Please use credentials with Manager or ContentReader+Writer role")
            return False
    
    def log(self, message):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def get_process_documents(self):
        """Get all documents associated with the process"""
        try:
            url = f"{self.server}/grc/api/contents/{self.process_id}/associations/children"
            headers = {"Accept": "application/json"}
            
            response = requests.get(url, auth=self.auth, headers=headers, timeout=30)
            
            if response.status_code == 200:
                children = response.json()
                # Filter only document types (typeDefinitionId 22 is SOXDocument)
                documents = [child for child in children if child.get('typeDefinitionId') in ['22', '42', '46']]
                return documents
            else:
                self.log(f"⚠ Error getting documents: HTTP {response.status_code}")
                return []
        except Exception as e:
            self.log(f"⚠ Exception getting documents: {str(e)}")
            return []
    
    def get_document_details(self, doc_id):
        """Get detailed information about a document"""
        try:
            url = f"{self.server}/grc/api/contents/{doc_id}"
            headers = {"Accept": "application/json"}
            
            response = requests.get(url, auth=self.auth, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            self.log(f"⚠ Exception getting document details: {str(e)}")
            return None
    
    def upload_to_cos_direct(self, file_content, filename):
        """Upload file content directly to IBM Cloud Object Storage"""
        if not self.cos_enabled:
            return False
        
        try:
            # Create object key with process folder structure
            object_key = f"Process_{self.process_id}/{filename}"
            
            # Upload directly from memory
            self.cos_client.put_object(
                Bucket=self.cos_bucket,
                Key=object_key,
                Body=file_content
            )
            
            self.log(f"☁️  Uploaded to COS: {object_key} ({len(file_content):,} bytes)")
            return True
        except Exception as e:
            self.log(f"⚠ Exception uploading to COS: {str(e)}")
            return False
    
    def download_document(self, doc_id, filename):
        """Download a document from OpenPages and upload directly to COS"""
        try:
            url = f"{self.server}/grc/api/contents/{doc_id}/document"
            
            response = requests.get(url, auth=self.auth, timeout=60, stream=True)
            
            if response.status_code == 200:
                # Check if file with same name exists in COS
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(filename)
                unique_filename = f"{name}_{timestamp}{ext}"
                
                # Read content into memory
                file_content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    file_content += chunk
                
                file_size = len(file_content)
                self.log(f"✓ Downloaded: {unique_filename} ({file_size:,} bytes)")
                
                # Upload directly to IBM Cloud Object Storage
                if self.cos_enabled:
                    self.upload_to_cos_direct(file_content, unique_filename)
                else:
                    self.log(f"⚠ COS not enabled - document not saved anywhere!")
                
                return True
            else:
                self.log(f"⚠ Failed to download document {doc_id}: HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log(f"⚠ Exception downloading document: {str(e)}")
            return False
    
    def check_for_new_documents(self):
        """Check for new documents and download them"""
        documents = self.get_process_documents()
        
        if not documents:
            self.log(f"ℹ No documents found in process {self.process_id}")
            return
        
        new_docs_found = False
        
        for doc in documents:
            doc_id = doc.get('id')
            
            if doc_id not in self.known_documents:
                # New document found!
                new_docs_found = True
                self.log(f"🆕 NEW DOCUMENT DETECTED: ID {doc_id}")
                
                # Get document details to get the filename
                details = self.get_document_details(doc_id)
                
                if details:
                    # Extract filename from path or use name
                    path = details.get('path', '')
                    filename = os.path.basename(path) if path else details.get('name', f'document_{doc_id}.bin')
                    
                    self.log(f"   Filename: {filename}")
                    self.log(f"   Path: {path}")
                    
                    # Download the document
                    if self.download_document(doc_id, filename):
                        # Add to known documents
                        self.known_documents.add(doc_id)
                        self.log(f"✓ Successfully processed document {doc_id}")
                    else:
                        self.log(f"✗ Failed to download document {doc_id}")
                else:
                    self.log(f"⚠ Could not get details for document {doc_id}")
        
        if not new_docs_found:
            self.log(f"ℹ No new documents (currently tracking {len(self.known_documents)} documents)")
    
    def initialize_known_documents(self):
        """Download all existing documents, then start monitoring for new ones"""
        self.log("Initializing - scanning for existing documents...")
        documents = self.get_process_documents()
        
        if not documents:
            self.log("ℹ No existing documents found in process")
            self.log(f"✓ Monitoring started - will check every {self.check_interval} seconds")
            return
        
        self.log(f"📥 Found {len(documents)} existing document(s) - downloading all...")
        self.log("-" * 70)
        
        # Download all existing documents
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get('id')
            
            self.log(f"Processing existing document {i}/{len(documents)}: ID {doc_id}")
            
            # Get document details to get the filename
            details = self.get_document_details(doc_id)
            
            if details:
                # Extract filename from path or use name
                path = details.get('path', '')
                filename = os.path.basename(path) if path else details.get('name', f'document_{doc_id}.bin')
                
                self.log(f"   Filename: {filename}")
                
                # Download the document
                if self.download_document(doc_id, filename):
                    # Add to known documents
                    self.known_documents.add(doc_id)
                    self.log(f"✓ Successfully processed existing document {doc_id}")
                else:
                    self.log(f"✗ Failed to download existing document {doc_id}")
                    # Still add to known documents to avoid retrying
                    self.known_documents.add(doc_id)
            else:
                self.log(f"⚠ Could not get details for document {doc_id}")
                # Still add to known documents
                self.known_documents.add(doc_id)
            
            self.log("-" * 70)
        
        self.log(f"✓ Downloaded {len(self.known_documents)} existing document(s)")
        self.log(f"✓ Now monitoring for NEW documents only - will check every {self.check_interval} seconds")
    
    def run(self):
        """Main monitoring loop"""
        self.log("=" * 70)
        self.log("OpenPages Document Monitor Started")
        self.log("=" * 70)
        self.log(f"Server: {self.server}")
        self.log(f"Process ID: {self.process_id}")
        self.log(f"Check Interval: {self.check_interval} seconds")
        if self.cos_enabled:
            self.log(f"COS Bucket: {self.cos_bucket}")
            self.log(f"COS Upload: ENABLED ☁️")
            self.log(f"Storage: Direct to Cloud (no local files)")
        else:
            self.log(f"⚠ COS Upload: DISABLED - Documents will NOT be saved!")
        self.log("=" * 70)
        
        # Initialize with existing documents
        self.initialize_known_documents()
        
        self.log("\n👀 Now monitoring for new documents... (Press Ctrl+C to stop)\n")
        
        try:
            while True:
                self.check_for_new_documents()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.log("\n" + "=" * 70)
            self.log("Monitor stopped by user")
            self.log(f"Total documents tracked: {len(self.known_documents)}")
            self.log("=" * 70)


# ============================================================================
# Flask HTTP Server for Health Checks
# ============================================================================

app = Flask(__name__)

# Global monitor instance
monitor_instance = None

@app.route('/')
def home():
    """Root endpoint"""
    return jsonify({
        'status': 'running',
        'service': 'OpenPages Document Monitor',
        'process_id': PROCESS_ID,
        'documents_tracked': len(monitor_instance.known_documents) if monitor_instance else 0
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/status')
def status():
    """Status endpoint with detailed information"""
    if monitor_instance:
        return jsonify({
            'status': 'running',
            'process_id': monitor_instance.process_id,
            'documents_tracked': len(monitor_instance.known_documents),
            'check_interval': monitor_instance.check_interval,
            'cos_enabled': monitor_instance.cos_enabled,
            'cos_bucket': monitor_instance.cos_bucket if monitor_instance.cos_enabled else None
        })
    return jsonify({'status': 'initializing'})

def run_monitor():
    """Run the document monitor in a separate thread"""
    global monitor_instance
    monitor_instance = OpenPagesDocumentMonitor(
        server=OPENPAGES_SERVER,
        username=USERNAME,
        password=PASSWORD,
        process_id=PROCESS_ID,
        check_interval=CHECK_INTERVAL_SECONDS,
        cos_api_key=COS_API_KEY,
        cos_instance_crn=COS_INSTANCE_CRN,
        cos_endpoint=COS_ENDPOINT,
        cos_bucket=COS_BUCKET_NAME
    )
    monitor_instance.run()

def main():
    """Main entry point"""
    # Start the monitor in a background thread
    monitor_thread = threading.Thread(target=run_monitor, daemon=True)
    monitor_thread.start()
    
    # Start Flask HTTP server on port 8080
    port = int(os.getenv('PORT', '8080'))
    print(f"\n🌐 Starting HTTP server on port {port}...")
    print(f"   Health check: http://localhost:{port}/health")
    print(f"   Status: http://localhost:{port}/status\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == "__main__":
    main()

# Made with Bob

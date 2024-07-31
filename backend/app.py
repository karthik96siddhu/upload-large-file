from flask import Flask, jsonify, request
import boto3
import os
from flask_cors import CORS
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# initialize s3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_DEFAULT_REGION')
)

# Set up logging
# logging.basicConfig(level=logging.DEBUG)

@app.route("/")
def home():
    return "<h1>Hello Welcome Home!</h1>"

@app.route('/list-buckets')
def list_buckets():
    try:
        # List S3 buckets
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(buckets)
        return jsonify(buckets)
    except Exception as e:
        return str(e), 500
    
@app.route("/create-multipart-upload", methods=['POST'])
def create_multipart_upload():
    data = request.get_json()
    file_name = data['fileName']
    bucket_name = os.getenv('S3_BUCKET_NAME')

# Debugging: Print bucket name and file name
    logging.debug(f"Bucket: {bucket_name}, File: {file_name}")
    logging.debug(f"Bucket Type: {type(bucket_name)}")

    # Ensure the bucket name is a valid string
    if not isinstance(bucket_name, str) or not bucket_name.strip():
        logging.error("Invalid S3 bucket name")
        return jsonify({'error': 'Invalid S3 bucket name'}), 400

    try:
        response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=file_name)
        return jsonify({'uploadId': response['UploadId']}), 200
    except Exception as e:
        logging.error(f"Error creating multipart upload: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route("/get-presigned-url", methods=['POST'])
def get_presigned_url():
    data = request.get_json()
    file_name = data['fileName']
    upload_id = data['uploadId']
    part_number = data['partNumber']
    bucket_name = os.getenv('S3_BUCKET_NAME')
    
    presigned_url = s3_client.generate_presigned_url(
        ClientMethod='upload_part',
        Params={
            'Bucket':bucket_name,
            'Key': file_name,
            'UploadId': upload_id,
            'PartNumber': part_number
        },
        ExpiresIn=3600
    )

    return jsonify({'url': presigned_url}), 200

@app.route('/complete-multipart-upload', methods=['POST'])
def complete_multipart_upload():
    data = request.get_json()
    file_name = data['fileName']
    upload_id = data['uploadId']
    parts = data['parts']

    bucket_name = os.getenv('S3_BUCKET_NAME')

    response = s3_client.complete_multipart_upload(
        Bucket = bucket_name,
        Key = file_name,
        UploadId = upload_id,
        MultipartUpload={'Parts': parts}
    )

    return jsonify({'location': response['Location']}), 200

if __name__ == '__main__':
    app.run(debug=True)
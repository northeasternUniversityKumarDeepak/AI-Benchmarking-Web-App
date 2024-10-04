import os
import subprocess
import boto3
import io
from pathlib import Path

# Initialize the S3 client
s3 = boto3.client('s3')



# Define the Hugging Face repo URL and S3 bucket name
repo_url = "https://huggingface.co/datasets/gaia-benchmark/GAIA.git"
# "https://huggingface.co/datasets/gaia-benchmark/GAIA.git"
local_repo_path = "./GAIA"
bucket_name = "bigdatadamg7245"
s3_folder = "staging/"  # Folder inside the S3 bucket to upload the dataset

# Clone the repository to local
def clone_repo(repo_url, local_path):
    if not os.path.exists(local_path):
        print(f"Cloning repository {repo_url} into {local_path}...")
        subprocess.run(["git", "clone", repo_url, local_path])
    else:
        print(f"Repository already exists at {local_path}")

# Upload a file to S3
def upload_file_to_s3(file_path, bucket_name, object_name):
    print(f"Uploading {file_path} to s3://{bucket_name}/{object_name}...")
    with open(file_path, "rb") as file_data:
        s3.upload_fileobj(file_data, bucket_name, object_name)

# Upload all files in the cloned repository to S3
def upload_repo_to_s3(local_repo_path, bucket_name, s3_folder):
    for root, dirs, files in os.walk(local_repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Generate the relative path for the object in S3
            relative_path = os.path.relpath(file_path, local_repo_path)
            s3_object_name = os.path.join(s3_folder, relative_path)
            upload_file_to_s3(file_path, bucket_name, s3_object_name)

# Run the process
# clone_repo(repo_url, local_repo_path)
upload_repo_to_s3(local_repo_path, bucket_name, s3_folder)

# print("All files uploaded to S3 successfully.")

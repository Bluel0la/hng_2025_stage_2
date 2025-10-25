import boto3

AWS_ACCESS_KEY_ID = "0751eafbf6934156b3ba86fdef0a7d8f"
AWS_SECRET_ACCESS_KEY = (
    "d3b7c7f49aa71207ae977308d07a005b8f2cd35025208e823118e7d6cbd81d7a"
)

s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    endpoint_url="https://objstorage.leapcell.io",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

BUCKET_NAME = "os-wsp1980603830540251137-vs3x-yv5n-h4cxpsz2"
response = s3.list_objects_v2(Bucket=BUCKET_NAME)
for obj in response.get("Contents", []):
    print(obj["Key"])

files = s3.list_objects_v2(Bucket=BUCKET_NAME)
print([f["Key"] for f in files.get("Contents", [])])

import csv
import dotenv
import os
import re

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
from datetime import timedelta

dotenv.load_dotenv()

username = os.getenv("CB_USERNAME")
password = os.getenv("CB_PASSWORD")
bucket_name = "ecommerce"

# Connect options - authentication
auth = PasswordAuthenticator(
    username,
    password,
)

cluster = Cluster(str(os.getenv("CB_CONN_STRING")), ClusterOptions(auth))

# Wait until the cluster is ready for use.
cluster.wait_until_ready(timedelta(seconds=5))

# get a reference to our bucket
cb = cluster.bucket(bucket_name)

cb_coll = cb.scope("devices").collection("smartphones")


def upsert_document(doc):
    print("\nUpsert CAS: ")
    try:
        key = doc["name"]
        result = cb_coll.upsert(key, doc)
        print(result.cas)
    except Exception as e:
        print(e)


with open("./dataset/smartphones.csv", "r") as file:
    reader = csv.DictReader(file)

    for item in reader:
        result = {}
        try:
            result["name"] = item["model"]
            storage_num = re.findall(r"\d+", item["ram"])
            storage_num = [int(num) for num in storage_num]
            result["ram"] = storage_num[0]
            result["storage"] = storage_num[1]
            result["rating"] = int(item["rating"]) if item["rating"] else 0
            result["price"] = int(item["price"][1:].replace(",", ""))
            result["display"] = item["display"].replace("\u2009", " ")
            upsert_document(result)
        except Exception:
            pass

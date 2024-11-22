import dotenv
import os


# needed for any cluster connection
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster

# needed for options -- cluster, timeout, SQL++ (N1QL) query, etc.
from couchbase.options import ClusterOptions
from datetime import timedelta
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L12-v2")


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

# Query to fetch all document IDs
query = "SELECT meta().id FROM ecommerce.devices.smartphones"
result = cluster.query(query)

counter = 0
successful = 0
for doc in result:
    try:
        key = doc["id"]
        result = cb_coll.get(key).content_as[dict]
        description = result["display"]
        vector = model.encode(description).astype(float).tolist()
        result["vec"] = vector
        cb_coll.upsert(key, result)
        print(f"Doc number {counter} upserted successfully")
        counter += 1
        successful += 1
    except Exception as ex:
        print(ex)
        counter += 1


print(f"Upserted {successful} / {counter} documents successfully\n")

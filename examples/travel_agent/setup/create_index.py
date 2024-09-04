import dotenv
import http
import os
import requests


def create_vector_index() -> None:
    hostname = os.getenv("CB_CONN_STRING").replace("couchbase", "http")
    response = requests.put(
        f"{hostname}:8094/api/bucket/travel-sample/scope/inventory/index/articles-index",
        headers={"Content-Type": "application/json"},
        auth=(
            os.getenv("CB_USERNAME"),
            os.getenv("CB_PASSWORD"),
        ),
        json={
            "name": "articles-index",
            "type": "fulltext-index",
            "params": {
                "doc_config": {
                    "docid_prefix_delim": "",
                    "docid_regexp": "",
                    "mode": "scope.collection.type_field",
                    "type_field": "type",
                },
                "mapping": {
                    "default_analyzer": "standard",
                    "default_datetime_parser": "dateTimeOptional",
                    "default_field": "_all",
                    "default_mapping": {"dynamic": False, "enabled": False},
                    "default_type": "_default",
                    "docvalues_dynamic": False,
                    "index_dynamic": False,
                    "store_dynamic": False,
                    "type_field": "_type",
                    "types": {
                        "inventory.article": {
                            "dynamic": False,
                            "enabled": True,
                            "properties": {
                                "vec": {
                                    "enabled": True,
                                    "dynamic": False,
                                    "fields": [
                                        {
                                            "dims": 384,
                                            "index": True,
                                            "name": "vec",
                                            "similarity": "dot_product",
                                            "type": "vector",
                                            "vector_index_optimized_for": "recall",
                                        }
                                    ],
                                }
                            },
                        }
                    },
                },
                "store": {"indexType": "scorch", "segmentVersion": 16},
            },
            "sourceType": "gocbcore",
            "sourceName": "travel-sample",
            "sourceParams": {},
            "planParams": {"maxPartitionsPerPIndex": 1024, "indexPartitions": 1, "numReplicas": 0},
        },
    )
    assert response.status_code == http.HTTPStatus.OK


if __name__ == "__main__":
    dotenv.load_dotenv(".env")
    create_vector_index()

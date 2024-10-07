if __name__ == "__main__":
    # TODO: This a WIP.
    import couchbase.auth
    import couchbase.cluster
    import couchbase.options
    import dotenv
    import os

    dotenv.load_dotenv()

    conn_opts = couchbase.options.ClusterOptions(
        authenticator=couchbase.auth.PasswordAuthenticator(
            os.getenv("AGENT_CATALOG_USER"), os.getenv("AGENT_CATALOG_PASSWORD")
        )
    )
    cluster = couchbase.cluster.Cluster.connect(os.getenv("AGENT_CATALOG_CONN_STRING"), conn_opts)
    bucket_name = os.getenv("AGENT_CATALOG_BUCKET")

    # Grab all exchanges (we need to transpose our exchanges)
    query = cluster.analytics_query("""
        WITH
            ...
        SELECT
            () AS question,
            () AS answer,
            () AS contexts
    """)
    result = list(query)

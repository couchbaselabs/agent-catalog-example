import couchbase.auth
import couchbase.cluster
import couchbase.options
import dotenv
import newspaper
import os
import semchunk
import sentence_transformers
import typing
import uuid

_ARTICLES = [
    "https://www.aaa.com/tripcanvas/article/top-vacations-spots-in-the-us-CM817",
    "https://www.travelandleisure.com/best-places-to-go-2024-8385979",
    "https://www.buzzfeed.com/hannahloewentheil/better-than-expected-travel-destinations",
]
_MODEL: sentence_transformers.SentenceTransformer = None
_CLUSTER: couchbase.cluster.Cluster = None


def grab_articles() -> typing.Iterable[typing.Dict]:
    # As a first approach, we can leverage newspaper to do some pre-processing.
    for article_url in _ARTICLES:
        article = newspaper.build_article(article_url)
        article.download()
        article.parse()
        yield {"text": article.text, "url": article_url}


def chunk_articles(articles: typing.Iterable[typing.Dict]) -> typing.Iterable[typing.Dict]:
    chunker = semchunk.chunkerify(_MODEL.tokenizer, chunk_size=256)
    for article in articles:
        for text_chunk in chunker(article["text"]):
            yield {"text": text_chunk, "url": article["url"]}


def generate_records(chunks: typing.Iterable[typing.Dict]) -> typing.Iterable[typing.Dict]:
    for chunk in chunks:
        embedding = _MODEL.encode([chunk["text"]])
        yield {
            "vec": list(embedding[0].astype("float64")),
            "text": chunk["text"],
            "type": "article",
            "url": chunk["url"],
        }


def ingest_records(records: typing.Iterable[typing.Dict]) -> None:
    bucket = _CLUSTER.bucket("travel-sample")
    collection = bucket.scope("inventory").collection("article")
    for r in records:
        k = "article_" + str(uuid.uuid4())
        collection.upsert(k, r)


if __name__ == "__main__":
    dotenv.load_dotenv(".env")
    _MODEL = sentence_transformers.SentenceTransformer(
        os.getenv("DEFAULT_SENTENCE_EMODEL"), tokenizer_kwargs={"clean_up_tokenization_spaces": True}
    )

    # Create the article collection.
    _CLUSTER = couchbase.cluster.Cluster(
        os.getenv("CB_CONN_STRING"),
        couchbase.options.ClusterOptions(
            couchbase.auth.PasswordAuthenticator(username=os.getenv("CB_USERNAME"), password=os.getenv("CB_PASSWORD"))
        ),
    )
    _CLUSTER.query("CREATE COLLECTION `travel-sample`.`inventory`.`article` IF NOT EXISTS;").execute()

    # Run a pipeline to ingest chunked articles.
    ingest_records(generate_records(chunk_articles(grab_articles())))

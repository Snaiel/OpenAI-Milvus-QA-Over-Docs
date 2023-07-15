from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.milvus import Milvus
from langchain.embeddings.openai import OpenAIEmbeddings
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, connections, utility
from typing import Dict, List, Tuple
import textwrap

DOCUMENTS_STORE_NAME = "OpenAI_QA_Over_Docs_Sources"

vector_store: Milvus

connections.connect()

def collection_exists():
    return utility.has_collection(DOCUMENTS_STORE_NAME)

def create_collection():
    if utility.has_collection(DOCUMENTS_STORE_NAME):
        print(f"Dropping {DOCUMENTS_STORE_NAME} collection")
        collection = Collection(DOCUMENTS_STORE_NAME)
        collection.drop()

    print(f"Creating {DOCUMENTS_STORE_NAME} collection")
    # 1. define fields
    fields = [
        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65_535),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1536),
        FieldSchema(name='metadata', dtype=DataType.JSON)
    ]
    # 2. enable dynamic schema in schema definition
    schema = CollectionSchema(
            fields, 
            "Documents as context to give to OpenAI's chat completion API"
    )

    # 3. reference the schema in a collection
    collection = Collection(DOCUMENTS_STORE_NAME, schema)

    # 4. index the vector field and load the collection
    index_params = {
        "metric_type": "L2",
        "index_type": "HNSW",
        "params": {"M": 8, "efConstruction": 64},
    }

    collection.create_index(
        field_name="vector", 
        index_params=index_params
    )

    # 5. load the collection
    collection.load()
    print(f"{DOCUMENTS_STORE_NAME} collection loaded")

    global vector_store
    vector_store = Milvus(embeddings, DOCUMENTS_STORE_NAME)

def add_sources(sources: list[str]):
    print(f"Adding sources to {DOCUMENTS_STORE_NAME} collection")
    loader = WebBaseLoader(web_path=sources)
    docs = loader.load()

    for doc in docs:
        doc.metadata = {'metadata': doc.metadata}

    text_splitter = RecursiveCharacterTextSplitter()

    docs = text_splitter.split_documents(docs)
    vector_store.add_documents(docs)

def delete_collection():
    if utility.has_collection(DOCUMENTS_STORE_NAME):
        print(f"Dropping {DOCUMENTS_STORE_NAME} collection")
        collection = Collection(DOCUMENTS_STORE_NAME)
        collection.drop()

# create_collection()

print("retrieving HuggingFace embeddings")
embeddings = OpenAIEmbeddings()

if utility.has_collection(DOCUMENTS_STORE_NAME):
    print(f"retrieving {DOCUMENTS_STORE_NAME} collection")
    vector_store = Milvus(embeddings, DOCUMENTS_STORE_NAME)
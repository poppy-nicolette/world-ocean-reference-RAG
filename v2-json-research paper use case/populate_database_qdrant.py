# https://www.perplexity.ai/search/import-argparse-import-os-impo-Swj60ceSQl.BDxG5e4_EcQ

import argparse
import os
import shutil
import time
# from langchain.document_loaders.pdf import PyPDFDirectoryLoader
# from langchain_community.document_loaders import PyPDFDirectoryLoader
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

from langchain_community.document_loaders import TextLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
from get_embedding_function import get_embedding_function
# from langchain.vectorstores.chroma import Chroma
from langchain_community.vectorstores import Chroma

CHROMA_PATH = "chroma"
DATA_PATH = "txt_data"



def main():

    # Initialize Qdrant client
    client = QdrantClient("localhost", port=6333)

    # Create a collection
    client.recreate_collection(
        collection_name="my_collection",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )


    # Check if the database should be cleared (using the --clear flag).
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    args = parser.parse_args()
    # if args.reset:
    #     print("✨ Clearing Database")
    #     clear_database()

    # Create (or update) the data store.
    documents = load_documents()
    chunks = split_documents(documents)
    # add_to_chroma(chunks)
    add_to_qdrant(client, chunks)


def load_documents():
    documents = []
    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".txt"):
            file_path = os.path.join(DATA_PATH, filename)
            loader = TextLoader(file_path)
            documents.extend(loader.load())
    return documents


def split_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

# Function to add documents in batches
def add_to_qdrant(chunks, batch_size=100):
    chunks_with_ids = calculate_chunk_ids(chunks)
    
    total_chunks = len(chunks_with_ids)
    print(f"Total new chunks to add: {total_chunks}")

    if total_chunks:
        for i in range(0, total_chunks, batch_size):
            start_time = time.time()
            batch = chunks_with_ids[i:i+batch_size]

            batch_texts = [chunk.page_content for chunk in batch]
            
            # Generate embeddings for the batch
            embeddings = embedding_function.embed_documents(batch_texts)
            
            # Prepare points in the correct format for Qdrant
            points = [
                PointStruct(
                    id=chunk.metadata["id"],
                    vector=embedding,
                    payload=chunk.metadata
                )
                for chunk, embedding in zip(batch, embeddings)
            ]
            
            client.upsert(
                collection_name="my_collection",
                points=points
            )
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            chunks_added = min(i+batch_size, total_chunks)
            chunks_remaining = total_chunks - chunks_added
            
            print(f"Progress: {chunks_added}/{total_chunks} chunks added, {chunks_remaining} remaining")
            print(f"Batch processing time: {elapsed_time:.2f} seconds")
            print(f"Estimated time remaining: {(elapsed_time * chunks_remaining / batch_size) / 60:.2f} minutes")

    else:
        print("No new chunks to add")


def add_to_chroma(chunks):
    db = Chroma(
        persist_directory=CHROMA_PATH, embedding_function=get_embedding_function()
    )

    chunks_with_ids = calculate_chunk_ids(chunks)

    existing_items = db.get(include=[])
    existing_ids = set(existing_items["ids"])
    print(f"Number of existing documents in DB: {len(existing_ids)}")

    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    total_new_chunks = len(new_chunks)
    print(f"Total new chunks to add: {total_new_chunks}")

    if total_new_chunks:
        batch_size = 100  # You can adjust this value based on your system's capabilities
        for i in range(0, total_new_chunks, batch_size):
            start_time = time.time()

            batch = new_chunks[i:i+batch_size]
            batch_ids = [chunk.metadata["id"] for chunk in batch]
            db.add_documents(batch, ids=batch_ids)
            db.persist()
            
            chunks_added = i + len(batch)
            chunks_remaining = total_new_chunks - chunks_added

            print(f"Progress: {chunks_added}/{total_new_chunks} chunks added, {chunks_remaining} remaining | time taken: {time.time()-start_time}")

        print("✅ All new documents have been added to the database")
    else:
        print("✅ No new documents to add")

def calculate_chunk_ids(chunks):
    last_file_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        file_id = os.path.basename(source).split('.')[0]  # Get the ID from the filename
        current_file_id = file_id

        if current_file_id == last_file_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_file_id}:{current_chunk_index}"
        last_file_id = current_file_id

        chunk.metadata["id"] = chunk_id

    return chunks

# def calculate_chunk_ids(chunks):
#     last_page_id = None
#     current_chunk_index = 0

#     for chunk in chunks:
#         source = chunk.metadata.get("source")
#         page = chunk.metadata.get("page")
#         current_page_id = f"{source}:{page}"

#         # If the page ID is the same as the last one, increment the index.
#         if current_page_id == last_page_id:
#             current_chunk_index += 1
#         else:
#             current_chunk_index = 0

#         # Calculate the chunk ID.
#         chunk_id = f"{current_page_id}:{current_chunk_index}"
#         last_page_id = current_page_id

#         # Add it to the page meta-data.
#         chunk.metadata["id"] = chunk_id

#     return chunks


def clear_database():
    if os.path.exists(CHROMA_PATH):
    #     shutil.rmtree(CHROMA_PATH)
        pass


if __name__ == "__main__":
    main()



############################################## RUN QDRANT LOCALLY
# docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant
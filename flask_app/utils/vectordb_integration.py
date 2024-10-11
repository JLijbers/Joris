import os
import re
import json
import time

from config import IGNORE_PATH

from pinecone import ServerlessSpec
from pinecone.grpc import PineconeGRPC
from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore


def load_docs(directory):
    """
    Args:
        directory (str): The root directory from which to load documents.

    Returns:
        list: A list of `Document` objects, each containing the text content of a file
              and metadata about its source.

    This function recursively searches the specified directory and its subdirectories
    for text files, loading their contents into a list of `Document` objects. It excludes
    files and directories based on the configurations in IGNORE_PATH.
    """

    # Load ignore configurations from IGNORE_PATH
    with open(IGNORE_PATH, 'r') as f:
        ignore = json.load(f)

    docs = []

    # Recursively traverse the directory and its subdirectories
    for root, dirs, files in os.walk(directory):
        # Skip directories specified
        dirs[:] = [d for d in dirs if d not in ignore['ignored_directories']]

        for file in files:
            # Skip files with extensions in the 'ignored_extensions' list or specific ignored files
            if any(file.endswith(ext) for ext in ignore['ignored_extensions']) or file in ignore['ignored_files']:
                continue

            # Create the full path to the current file
            path = os.path.join(root, file)

            # Open the file and read its content
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                # Create a Document object with metadata and text content
                docs.append(Document(metadata={'source': path, 'file': file}, page_content=f.read()))

    return docs


def split_docs(code_files, chunk_size=6000, chunk_overlap=200):
    """Split the input documents into smaller chunks."""
    python_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    docs = python_splitter.split_documents(code_files)
    return docs


class VectorDBIntegration:
    def __init__(self, vectordb_api_key, index_name):
        self.vectordb_api_key = vectordb_api_key
        self.index_name = self.sanitize_index_name(index_name.lower())
        self.embeddings = OpenAIEmbeddings()
        self.pc = PineconeGRPC(api_key=self.vectordb_api_key)

    @staticmethod
    def sanitize_index_name(index_name):
        # Replace underscores with hyphens
        index_name = index_name.replace('_', '-')
        # Remove any characters that are not lower case alphanumeric or hyphens
        index_name = re.sub(r'[^a-z0-9-]', '', index_name)
        return index_name

    def index_exists(self):
        # Get a list of all indexes in Pinecone
        existing_indexes = self.pc.list_indexes().names()

        # Check if our index name is among them
        return self.index_name in existing_indexes

    def is_index_populated(self):
        """Check if the Pinecone index is populated by running a sample query."""
        # Connect to the existing index
        db = PineconeVectorStore.from_existing_index(self.index_name, self.embeddings)

        # Run a sample query
        matched_docs = db.similarity_search("function", k=1)

        # Check if any results are returned
        return len(matched_docs) > 0

    def create_index(self):
        self.pc.create_index(self.index_name, dimension=1536,
                             metric='cosine',
                             spec=ServerlessSpec(
                                 cloud='aws',
                                 region='us-east-1'
                             ))
        # Wait to give Pinecone time to process new index before populating
        time.sleep(10)

    def embed_and_store(self, directory):
        # Read and split files from codebase
        print("Embedding and storing codebase to vector database index..")
        documents = load_docs(directory)
        splitted_docs = split_docs(documents)

        # Embed split code files and store in vector database
        index = PineconeVectorStore.from_documents(splitted_docs, self.embeddings, index_name=self.index_name)

        return index

    def flush_index(self):
        self.pc.delete_index(self.index_name)
        self.create_index()

    def retrieve_embeddings(self, search_string, k, file=None):
        code_str = ""

        db = PineconeVectorStore.from_existing_index(self.index_name, self.embeddings)

        # Search indexed codebase based on search string
        if file:
            matched_docs = db.similarity_search(search_string, k=k, filter={"file": file})
        else:
            matched_docs = db.similarity_search(search_string, k=k)

        # Paste results in one string
        for doc in matched_docs:
            code_str += "THE CODE CHUNK BELOW IS FROM THIS FILE: " + doc.metadata['source'] + "\n"
            if "content_type" in doc.metadata:
                code_str += "THE CODE CHUNK BELOW IS OF THIS CONTENT_TYPE: " + doc.metadata['content_type'] + "\n\n"
            code_str += doc.page_content + "\n\n\n <ANOTHER POSSIBLY RELEVANT CODE CHUNK BELOW> \n\n\n"

        return code_str

    def search_vectordb(self, code_needed):
        code_str = ""
        seen_strings = set()

        # split the string into a list of lines
        code_needed_split = code_needed.split("\n")

        # loop over the lines
        for code in code_needed_split:
            # get file-name
            file = code.split(' ')[0]
            string = self.retrieve_embeddings(code, k=1, file=file)
            # Check if the string has not been encountered before
            if string not in seen_strings:
                code_str += string
                seen_strings.add(string)

        return code_str

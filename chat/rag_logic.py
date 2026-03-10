import os
import shutil
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import chromadb

print("--- RAG Logic Module Loaded Successfully ---")

persist_directory = 'db_storage'
upload_directory = 'uploads'

os.makedirs(upload_directory, exist_ok=True)

# Embedding model (shared — stateless, safe to reuse)
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def get_vectorstore(user_id: int):
    """
    Returns a ChromaDB-backed vectorstore scoped to a specific user.
    Each user gets their own collection: 'user_docs_<user_id>'
    """
    client = chromadb.PersistentClient(path=persist_directory)
    return Chroma(
        client=client,
        embedding_function=embedding_model,
        collection_name=f"user_docs_{user_id}",
    )


# Custom prompt — reduces hallucinations
qa_prompt = PromptTemplate(
    template="""
You are a helpful assistant.
Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't know".

Context:
{context}

Question:
{question}
""",
    input_variables=["context", "question"],
)


def ingest_file(file_path: str, user_id: int) -> str:
    """Ingest a PDF or DOCX file into the user's vector store."""
    filename = os.path.basename(file_path)

    # Save a copy in uploads/<user_id>/
    user_upload_dir = os.path.join(upload_directory, str(user_id))
    os.makedirs(user_upload_dir, exist_ok=True)
    target_path = os.path.join(user_upload_dir, filename)
    shutil.copy(file_path, target_path)

    # Load document
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    else:
        loader = Docx2txtLoader(file_path)

    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = splitter.split_documents(docs)

    vstore = get_vectorstore(user_id)
    vstore.add_documents(splits)
    return "Success"


def ask_question(query: str, user_id: int, target_file: str = None) -> str:
    """Answer a question using the user's private vector store."""
    vectorstore = get_vectorstore(user_id)

    search_kwargs = {"k": 5}
    if target_file:
        search_kwargs["filter"] = {"source": {"$contains": target_file}}

    llm = Ollama(model="llama3")
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs),
        chain_type="stuff",
        chain_type_kwargs={"prompt": qa_prompt},
    )
    response = chain.invoke(query)
    return response['result']


def list_documents(user_id: int) -> list:
    """List all documents ingested by this user."""
    vstore = get_vectorstore(user_id)
    data = vstore.get()
    if data['metadatas']:
        return list(set([os.path.basename(m['source']) for m in data['metadatas']]))
    return []


def delete_document(filename: str, user_id: int) -> bool:
    """Delete a document from the user's vector store."""
    vstore = get_vectorstore(user_id)
    data = vstore.get()

    ids_to_delete = [
        data['ids'][i]
        for i, m in enumerate(data['metadatas'])
        if filename in m['source']
    ]

    if ids_to_delete:
        vstore.delete(ids=ids_to_delete)
        # Also remove the physical file
        user_file_path = os.path.join(upload_directory, str(user_id), filename)
        try:
            if os.path.exists(user_file_path):
                os.remove(user_file_path)
        except Exception:
            pass
        return True
    return False
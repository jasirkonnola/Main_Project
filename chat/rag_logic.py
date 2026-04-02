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
    template="""You are an intelligent academic assistant for college notes. Your role is to help students understand their course material accurately and clearly.

## Instructions
- Answer the question using ONLY the information provided in the context below.
- Be concise but thorough. If the question requires a detailed explanation, provide one.
- If the context contains partial information, share what is available and note what is incomplete.
- If the answer is genuinely not in the context, respond: "I don't have enough information in the provided notes to answer this question."
- Never fabricate or assume information not present in the context.
- Use clear formatting (bullet points, numbered lists, or short paragraphs) based on what best suits the answer.
- If the question is a definition, start with a direct one-line definition before elaborating.
- If the question involves steps or a process, present them in order.

## Context (from uploaded notes):
{context}

## Question:
{question}

## Answer:""",
    input_variables=["context", "question"],
)


def ingest_file(file_path: str, user_id: int, session_id: str = None) -> str:
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
    
    if session_id:
        for split in splits:
            split.metadata['session_id'] = session_id
            
    vstore.add_documents(splits)
    return "Success"


def ask_question(query: str, user_id: int, target_file: str = None, session_id: str = None) -> str:
    """Answer a question using the user's private vector store."""
    vectorstore = get_vectorstore(user_id)

    search_filter = {}
    if target_file and session_id:
        search_filter = {"$and": [{"source": {"$contains": target_file}}, {"session_id": session_id}]}
    elif target_file:
        search_filter = {"source": {"$contains": target_file}}
    elif session_id:
        search_filter = {"session_id": session_id}

    search_kwargs = {"k": 5}
    if search_filter:
        search_kwargs["filter"] = search_filter

    llm = Ollama(model="llama3")
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs),
        chain_type="stuff",
        chain_type_kwargs={"prompt": qa_prompt},
    )
    response = chain.invoke(query)
    return response['result']


def list_documents(user_id: int, session_id: str = None) -> list:
    """List all documents ingested by this user for a session."""
    vstore = get_vectorstore(user_id)
    data = vstore.get()
    
    docs = []
    if data['metadatas']:
        for m in data['metadatas']:
            if session_id and m.get('session_id') != session_id:
                continue
            docs.append(os.path.basename(m['source']))
    return list(set(docs))


def delete_document(filename: str, user_id: int, session_id: str = None) -> bool:
    """Delete a document from the user's vector store."""
    vstore = get_vectorstore(user_id)
    data = vstore.get()

    ids_to_delete = []
    for i, m in enumerate(data['metadatas']):
        if filename in m.get('source', ''):
            if session_id and m.get('session_id') != session_id:
                continue
            ids_to_delete.append(data['ids'][i])

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
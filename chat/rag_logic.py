import os
import shutil
import glob
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
import chromadb

print("--- RAG Logic Module Loaded Successfully ---")

persist_directory = 'db_storage'
upload_directory = 'uploads'

os.makedirs(upload_directory, exist_ok=True)

# ---------------------------------------------------------
# RESTART CLEANUP LOGIC: Clear old vectors and files on boot
# ---------------------------------------------------------

# This model converts text into numbers (embeddings)
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vectorstore():
    client = chromadb.PersistentClient(path=persist_directory)
    return Chroma(client=client, embedding_function=embedding_model, collection_name="my_docs")

# Initialize LLM once globally to save time on every query
llm = Ollama(model="llama3") 

# Load existing vector database once
vectorstore = get_vectorstore()
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())

def ingest_file(file_path):
    filename = os.path.basename(file_path) 
    target_path = os.path.join(upload_directory, filename) 
    shutil.copy(file_path, target_path)
    
    if file_path.endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    else:
        loader = Docx2txtLoader(file_path)
    
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(docs)
    
    # Store directly in our unified vectorstore configuration
    vstore = get_vectorstore()
    vstore.add_documents(splits)
    return "Success"

def get_answer(query):
    # We now use the globally initialized qa_chain instead of recreating it every time!
    response = qa_chain.invoke(query)
    return response['result']

def list_documents():
    vstore = get_vectorstore()
    data = vstore.get()
    if data['metadatas']:
        # Extract unique filenames cleanly using os.path.basename
        return list(set([os.path.basename(m['source']) for m in data['metadatas']]))
    return []

def delete_document(filename):
    vstore = get_vectorstore()
    data = vstore.get()
    ids_to_delete = [
        data['ids'][i] for i, m in enumerate(data['metadatas']) 
        if filename in m['source']
    ]
    if ids_to_delete:
        vstore.delete(ids=ids_to_delete)
        # Delete file from local storage to clean it up entirely
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception:
            pass
        return True
    return False

def ask_question(query, target_file=None):
    vectorstore = get_vectorstore()
    
    # If a specific file is selected, filter the search
    search_kwargs = {"k": 3}
    if target_file:
        search_kwargs["filter"] = {"source": {"$contains": target_file}}

    # We use the existing llama3 model. 
    # If you want to use llama3.2:1b, you MUST open a new terminal and run: `ollama pull llama3.2:1b`
    local_llm = Ollama(model="llama3")
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=local_llm, 
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs)
    )
    response = qa_chain.invoke(query)
    return response['result']
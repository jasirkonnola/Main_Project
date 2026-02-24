import os
import shutil
import glob
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

# ---------------------------------------------------------
# Removed restart cleanup logic (no auto-delete of DB/files)
# ---------------------------------------------------------

# Embedding model
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vectorstore():
    client = chromadb.PersistentClient(path=persist_directory)
    return Chroma(
        client=client,
        embedding_function=embedding_model,
        collection_name="my_docs"
    )


# Initialize LLM globally
llm = Ollama(model="llama3") 

# Load vectorstore once
vectorstore = get_vectorstore()

# Custom prompt template to reduce hallucinations
qa_prompt = PromptTemplate(
    template="""
    You are a helpful assistant. Use the following context to answer the question.
    If the answer is not in the context, say you don’t know.

    Context:
    {context}

    Question:
    {question}

    Answer:
    """,
    input_variables=["context", "question"]
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),  # retrieve more docs
    chain_type="stuff",
    chain_type_kwargs={"prompt": qa_prompt}
)

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
    
    vstore = get_vectorstore()
    vstore.add_documents(splits)
    return "Success"

def get_answer(query):
    response = qa_chain.invoke(query)
    return response['result']

def list_documents():
    vstore = get_vectorstore()
    data = vstore.get()
    if data['metadatas']:
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
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception:
            pass
        return True
    return False

def ask_question(query, target_file=None):
    vectorstore = get_vectorstore()
    
    search_kwargs = {"k": 5}  # retrieve more docs for better context
    if target_file:
        search_kwargs["filter"] = {"source": {"$contains": target_file}}

    local_llm = Ollama(model="llama3")
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=local_llm, 
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs),
        chain_type="stuff",
        chain_type_kwargs={"prompt": qa_prompt}
    )
    response = qa_chain.invoke(query)
    return response['result']

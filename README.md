# RAG PDF Assistant with Split-View

![App Screenshot](https://github.com/jasirkonnola/rag_project/blob/main/rag_project/DocuChat.png)

A sophisticated Django-based RAG (Retrieval-Augmented Generation) application that allows users to chat with their PDF documents. It features a modern **Gemini-style Split View** UI, where source documents are displayed side-by-side with the chat, automatically navigating to the exact page where the answer was found.

---

## ✨ Key Features

* **📚 RAG Pipeline**: Upload multiple PDFs and ask questions. The AI retrieves context-aware answers.
* **🖥️ Split-View Interface**:
  * **Chat on Left**: Clean, responsive chat interface.
  * **Source Viewer on Right**: Hidden by default, opens efficiently when needed.
* **🎯 Deep Linking**: Clicking a citation button ("Source Page 5") opens the **Full PDF** directly to that page using native browser PDF controls (zoom, search, print).
* **💾 Smart Persistence**:
  * Chat history is automatically saved to your local browser storage.
  * Messages persist even if you reload the page or delete a file.
* **🎨 Pro UI/UX**:
  * Clean filenames (hidden folders).
  * Instant delete with no annoying popups.
  * Modern Tailwind CSS styling.
* **🔒 Robust Security**:
  * Secure file handling.
  * `X-Frame-Options` configured to allow safe iframe embedding.

---

## 🛠️ Technology Stack

* **Backend**: Django 4.2.x, Python 3.10+
* **AI/RAG**: LangChain, LangChain-Community, LangChain-HuggingFace, ChromaDB, Ollama (local LLM runtime).
* **Frontend**: HTML5, Vanilla JavaScript, Tailwind CSS (CDN).
* **PDF Engine**: PyPDF for PDF parsing, Docx2txt for DOCX parsing.

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10 or higher.
* `pip` package manager.

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd rag_project

# Install Dependencies:
pip install django langchain langchain-community langchain-huggingface chromadb pypdf docx2txt ollama

# Apply Migrations:
python manage.py makemigrations
python manage.py migrate

# Run the Server:
python manage.py runserver

# Access the App:
Open http://127.0.0.1:8000/ (127.0.0.1 in Bing) in your browser.

#📖 Usage Guide
Upload: Click the Cloud icon or drag & drop PDFs into the sidebar.

Chat: Type your question in the bottom bar.

View Sources:

If the AI finds the answer in a PDF, a "Source Page X" button will appear.

Click it to split the screen and see the PDF page side-by-side.

Use the arrow icon in the viewer header to open the PDF in a new tab if needed.

Manage:

Click the Trash icon to instantly delete a document.

Click "Clear Conversation" in the sidebar to reset your chat history.


# 📂 Project Structure
```bash
Main Project/
│── manage.py
│── requirements.txt
│── db_storage/        # vector database storage
│── uploads/           # PDF/DOCX uploads
│── venv/              # virtual environment (ignored in Git)
│
├── rag_root/          # Django project root
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── chat/              # Django app
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── views.py
    ├── tests.py
    ├── rag_logic.py   # your RAG pipeline
    └── templates/
        ├── home.html
        └── index.html

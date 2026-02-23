from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import default_storage
from .rag_logic import ingest_file, get_answer, ask_question, list_documents, delete_document

def home(request):
    return render(request, 'home.html')

def chat_page(request):
    return render(request, 'index.html')

def upload_api(request):
    file = request.FILES.get('file')
    if file:
        file_name = default_storage.save(file.name, file)
        file_path = default_storage.path(file_name)
        ingest_file(file_path) # Process the file
        return JsonResponse({"status": "File processed!"})
    return JsonResponse({"status": "No file uploaded."}, status=400)

def ask_api(request):
    user_query = request.GET.get('question')
    target_file = request.GET.get('file')
    
    # We use ask_question to support the target_file filtering
    answer = ask_question(user_query, target_file)
    return JsonResponse({"answer": answer})

def get_files_api(request):
    files = list_documents()
    return JsonResponse({"files": files})

def delete_file_api(request):
    filename = request.GET.get('filename')
    success = delete_document(filename)
    return JsonResponse({"success": success})
from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods
from langchain_community.llms import Ollama

from .rag_logic import ingest_file, ask_question, list_documents, delete_document

import logging

logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'home.html')


def chat_page(request):
    return render(request, 'index.html')


@require_http_methods(["POST"])
def upload_api(request):
    file = request.FILES.get('file')

    if not file:
        return JsonResponse({"error": "No file provided."}, status=400)

    try:
        file_name = default_storage.save(file.name, file)
        file_path = default_storage.path(file_name)
        ingest_file(file_path)
        return JsonResponse({"status": "File processed!", "filename": file.name})
    except Exception as e:
        logger.exception("Failed to ingest file: %s", file.name)
        return JsonResponse({"error": "File processing failed.", "detail": str(e)}, status=500)


@require_http_methods(["GET"])
def ask_api(request):
    user_query = request.GET.get('question', '').strip()
    target_file = request.GET.get('file', '').strip() or None

    if not user_query:
        return JsonResponse({"error": "Missing required parameter: 'question'."}, status=400)

    try:
        answer = ask_question(user_query, target_file)
        return JsonResponse({"answer": answer})
    except Exception as e:
        logger.exception("Failed to answer question: %s", user_query)
        return JsonResponse({"error": "Could not process question.", "detail": str(e)}, status=500)


@require_http_methods(["GET"])
def get_files_api(request):
    try:
        files = list_documents()
        return JsonResponse({"files": files})
    except Exception as e:
        logger.exception("Failed to list documents.")
        return JsonResponse({"error": "Could not retrieve files.", "detail": str(e)}, status=500)


@require_http_methods(["DELETE"])
def delete_file_api(request):
    filename = request.GET.get('filename', '').strip()

    if not filename:
        return JsonResponse({"error": "Missing required parameter: 'filename'."}, status=400)

    try:
        success = delete_document(filename)
        if not success:
            return JsonResponse({"error": f"File '{filename}' not found or could not be deleted."}, status=404)
        return JsonResponse({"success": True, "deleted": filename})
    except Exception as e:
        logger.exception("Failed to delete document: %s", filename)
        return JsonResponse({"error": "Deletion failed.", "detail": str(e)}, status=500)


VALID_TABS = {'define', 'insight'}

@require_http_methods(["GET"])
def insight_api(request):
    word = request.GET.get('word', '').strip()
    tab  = request.GET.get('tab', 'define').strip()

    if not word:
        return JsonResponse({"error": "Missing required parameter: 'word'."}, status=400)

    if tab not in VALID_TABS:
        return JsonResponse({"error": f"Invalid tab. Must be one of: {', '.join(VALID_TABS)}."}, status=400)

    if tab == 'define':
        prompt = (
            f'Give a clear, concise dictionary-style definition of the word or phrase: "{word}".\n'
            "Format your response with:\n"
            "1. The part of speech (noun), (verb), etc.\n"
            "2. A clear definition (1-2 sentences)\n"
            "3. An example sentence using the word\n"
            "Keep it brief and simple. No markdown."
        )
    else:
        prompt = (
            f'Give an insightful AI explanation of the word or phrase: "{word}" as it might appear in a document.\n'
            "Include:\n"
            "1. What it means in plain English\n"
            "2. Why it matters or how it's typically used\n"
            "3. A related concept or synonym\n"
            "Keep it conversational, 3-5 sentences total. No markdown."
        )

    try:
        llm = Ollama(model="llama3")
        result = llm.invoke(prompt)
        return JsonResponse({"result": result})
    except Exception as e:
        logger.exception("Ollama inference failed for word: %s", word)
        return JsonResponse({"error": "AI inference failed.", "detail": str(e)}, status=500)
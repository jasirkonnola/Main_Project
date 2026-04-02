from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from langchain_community.llms import Ollama

from .rag_logic import ingest_file, ask_question, list_documents, delete_document
from .models import ChatMessage, ChatSession

import logging

logger = logging.getLogger(__name__)


# -----------------------------------------------
# Auth views
# -----------------------------------------------

def register_view(request):
    """User registration page."""
    if request.user.is_authenticated:
        return redirect('chat')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat')
    else:
        form = UserCreationForm()

    return render(request, 'auth/register.html', {'form': form})


# -----------------------------------------------
# Page views
# -----------------------------------------------

def home(request):
    return render(request, 'home.html')


@login_required
def chat_page(request):
    return render(request, 'index.html')


@login_required
def profile_view(request):
    """User profile page."""
    return render(request, 'profile.html')


# -----------------------------------------------
# API views (login required)
# -----------------------------------------------

@login_required
@require_http_methods(["POST"])
def upload_api(request):
    file = request.FILES.get('file')

    if not file:
        return JsonResponse({"error": "No file provided."}, status=400)

    session_id = request.POST.get('session_id')
    if not session_id:
        return JsonResponse({"error": "No session_id provided."}, status=400)

    # ensure session exists
    ChatSession.objects.get_or_create(id=session_id, user=request.user)

    try:
        file_name = default_storage.save(file.name, file)
        file_path = default_storage.path(file_name)
        ingest_file(file_path, user_id=request.user.id, session_id=session_id)
        return JsonResponse({"status": "File processed!", "filename": file.name})
    except Exception as e:
        logger.exception("Failed to ingest file: %s", file.name)
        return JsonResponse({"error": "File processing failed.", "detail": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def ask_api(request):
    user_query = request.GET.get('question', '').strip()
    target_file = request.GET.get('file', '').strip() or None

    if not user_query:
        return JsonResponse({"error": "Missing required parameter: 'question'."}, status=400)

    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({"error": "Missing session_id."}, status=400)

    session, _ = ChatSession.objects.get_or_create(id=session_id, user=request.user)

    try:
        answer = ask_question(user_query, user_id=request.user.id, target_file=target_file, session_id=session_id)
        if answer:
            ChatMessage.objects.create(session=session, user=request.user, query=user_query, answer=answer)
        return JsonResponse({"answer": answer})
    except Exception as e:
        logger.exception("Failed to answer question: %s", user_query)
        return JsonResponse({"error": "Could not process question.", "detail": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_files_api(request):
    session_id = request.GET.get('session_id')
    try:
        files = list_documents(user_id=request.user.id, session_id=session_id)
        return JsonResponse({"files": files})
    except Exception as e:
        logger.exception("Failed to list documents.")
        return JsonResponse({"error": "Could not retrieve files.", "detail": str(e)}, status=500)


@login_required
@require_http_methods(["GET", "DELETE"])
def delete_file_api(request):
    filename = request.GET.get('filename', '').strip()
    session_id = request.GET.get('session_id')

    if not filename:
        return JsonResponse({"error": "Missing required parameter: 'filename'."}, status=400)

    try:
        success = delete_document(filename, user_id=request.user.id, session_id=session_id)

        if not success:
            return JsonResponse(
                {"error": f"File '{filename}' not found or could not be deleted."},
                status=404,
            )

        return JsonResponse({"success": True, "deleted": filename})

    except Exception as e:
        logger.exception("Failed to delete document: %s", filename)
        return JsonResponse({"error": "Deletion failed.", "detail": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_chat_history_api(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({"history": []})
    try:
        messages = ChatMessage.objects.filter(user=request.user, session_id=session_id).order_by('created_at')
        history = [{"query": m.query, "answer": m.answer} for m in messages]
        return JsonResponse({"history": history})
    except Exception as e:
        logger.exception("Failed to retrieve chat history.")
        return JsonResponse({"error": "Could not retrieve history.", "detail": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_sessions_api(request):
    try:
        sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
        session_list = [{"id": str(s.id), "title": s.title} for s in sessions]
        return JsonResponse({"sessions": session_list})
    except Exception as e:
        logger.exception("Failed to retrieve sessions.")
        return JsonResponse({"error": "Failed to retrieve sessions.", "detail": str(e)}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def delete_chat_history_api(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({"error": "Missing session_id"}, status=400)
    try:
        ChatSession.objects.filter(id=session_id, user=request.user).delete()
        return JsonResponse({"success": True})
    except Exception as e:
        logger.exception("Failed to delete chat history.")
        return JsonResponse({"error": "Could not delete history.", "detail": str(e)}, status=500)


VALID_TABS = {'define', 'insight'}


@login_required
@require_http_methods(["GET"])
def insight_api(request):
    word = request.GET.get('word', '').strip()
    tab  = request.GET.get('tab', 'define').strip()

    if not word:
        return JsonResponse({"error": "Missing required parameter: 'word'."}, status=400)

    if tab not in VALID_TABS:
        return JsonResponse(
            {"error": f"Invalid tab. Must be one of: {', '.join(VALID_TABS)}."},
            status=400,
        )

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
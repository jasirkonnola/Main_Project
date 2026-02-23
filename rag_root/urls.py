from django.contrib import admin
from django.urls import path
from chat import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),             # Landing Page
    path('chat/', views.chat_page, name='chat'),   # Chat Interface
    path('upload/', views.upload_api),             # API for uploads
    path('ask/', views.ask_api),                   # API for questions
    path('api/files/', views.get_files_api),       # API to show sidebar files
    path('api/delete/', views.delete_file_api),    # API to delete files
]
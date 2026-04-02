from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from chat import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('login/',    auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/',   auth_views.LogoutView.as_view(),                               name='logout'),
    path('register/', views.register_view,                                           name='register'),
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='auth/password_change.html',
        success_url='/profile/',
    ), name='password_change'),

    # Pages
    path('',         views.home,         name='home'),
    path('chat/',    views.chat_page,    name='chat'),
    path('profile/', views.profile_view, name='profile'),

    # APIs
    path('upload/',      views.upload_api),
    path('ask/',         views.ask_api),
    path('api/files/',   views.get_files_api),
    path('api/sessions/', views.get_sessions_api),
    path('api/history/', views.get_chat_history_api),
    path('api/history/delete/', views.delete_chat_history_api),
    path('api/delete/',  views.delete_file_api),
    path('api/insight/', views.insight_api),
]
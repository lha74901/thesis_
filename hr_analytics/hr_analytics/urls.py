# hr_analytics/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

from employee_predictor import views


def root_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        return redirect('employee-portal')
    return redirect('login')

urlpatterns = [
    path('', root_redirect, name='root'),
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(
        template_name='employee_predictor/registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='login'
    ), name='logout'),
    
    path('register/', views.employee_register, name='register'),
    
    # Include the app URLs
    path('', include('employee_predictor.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
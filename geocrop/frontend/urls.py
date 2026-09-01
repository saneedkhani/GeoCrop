from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('upload/', views.upload_view, name='upload'),
    path('processing/', views.processing_view, name='processing'),
    path('results/', views.results_view, name='results'),
    path('api/fields/', views.field_data_view, name='field_data'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('api/dashboard-stats/', views.dashboard_stats_view, name='dashboard_stats'),
    path('profile/', views.profile_view, name='profile'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
]

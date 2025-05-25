from django.urls import path
from . import views
 
urlpatterns = [
    path('api/semantic-search/', views.semantic_search_view, name='semantic_search'),
] 
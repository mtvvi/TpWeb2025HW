from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('hot/', views.hot, name='hot'),
    path('tag/<str:tag_name>/', views.tag, name='tag'),
    path('login/', views.custom_login, name='login'),
    path('signup/', views.custom_signup, name='signup'),
    path('logout/', views.custom_logout, name='logout'),
    path('settings/', views.edit_profile, name='settings'),
    path('ask/', views.ask_question, name='ask'),
    path('question/<int:question_id>/', views.question_detail, name='question'),
    path('ajax/like_question/', views.like_question, name='ajax_like_question'),
    path('ajax/like_answer/', views.like_answer, name='ajax_like_answer'),
    path('ajax/mark_correct/', views.mark_correct, name='ajax_mark_correct'),
]
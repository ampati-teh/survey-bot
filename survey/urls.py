from django.urls import path
from . import views

# urlpatterns = [
#     path('', views.survey_list, name='survey_list'),
#     path('<int:survey_id>/', views.survey_editor, name='survey_editor'),
#
#     # API endpoints 4;O AJAX
#     path('api/survey/<int:survey_id>/update/', views.update_survey, name='update_survey'),
#     path('api/survey/<int:survey_id>/question/create/', views.create_question, name='create_question'),
#     path('api/question/<int:question_id>/update/', views.update_question, name='update_question'),
#     path('api/question/<int:question_id>/delete/', views.delete_question, name='delete_question'),
#     path('api/question/<int:question_id>/option/create/', views.create_option, name='create_option'),
#     path('api/option/<int:option_id>/update/', views.update_option, name='update_option'),
#     path('api/option/<int:option_id>/delete/', views.delete_option, name='delete_option'),
# ]

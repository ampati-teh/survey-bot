from django.shortcuts import render

# Create your views here.
# -*- coding: utf-8 -*-
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Max
from .models import Survey, Question, QuestionOption, Response
import json


@staff_member_required
def survey_list(request):
    """List of all surveys for editing"""
    surveys = Survey.objects.annotate(
        question_count=Count('questions'),
        response_count=Count('sessions__responses', distinct=True)
    ).order_by('-created_at')

    context = {
        'surveys': surveys,
        'title': 'Survey Management'
    }
    return render(request, 'admin/survey/survey_list.html', context)


@staff_member_required
def survey_editor(request, survey_id):
    """Survey editor page"""
    survey = get_object_or_404(Survey, pk=survey_id)
    questions = survey.questions.prefetch_related('options').order_by('order')

    # Get statistics for each question
    questions_with_stats = []
    for question in questions:
        total_responses = Response.objects.filter(question=question).count()

        # Option statistics (for choice questions)
        option_stats = []
        if question.question_type == 'choice':
            for option in question.options.all():
                count = Response.objects.filter(selected_option=option).count()
                percentage = (count / total_responses * 100) if total_responses > 0 else 0
                option_stats.append({
                    'text': option.text,
                    'count': count,
                    'percentage': round(percentage, 1)
                })

        questions_with_stats.append({
            'question': question,
            'total_responses': total_responses,
            'option_stats': option_stats
        })

    context = {
        'survey': survey,
        'questions_with_stats': questions_with_stats,
        'title': f'Editing: {survey.title}'
    }
    return render(request, 'admin/survey/survey_editor.html', context)


@staff_member_required
@require_http_methods(["POST"])
def update_survey(request, survey_id):
    """AJAX: update survey data"""
    survey = get_object_or_404(Survey, pk=survey_id)
    data = json.loads(request.body)

    if 'title' in data:
        survey.title = data['title']
    if 'description' in data:
        survey.description = data['description']
    if 'is_active' in data:
        survey.is_active = data['is_active']

    survey.save()
    return JsonResponse({'success': True})


@staff_member_required
@require_http_methods(["POST"])
def create_question(request, survey_id):
    """AJAX: create new question"""
    survey = get_object_or_404(Survey, pk=survey_id)
    data = json.loads(request.body)

    # Find max order
    max_order = survey.questions.aggregate(Max('order'))['order__max'] or 0

    question = Question.objects.create(
        survey=survey,
        text=data.get('text', 'New question'),
        question_type=data.get('question_type', 'text'),
        order=max_order + 1,
        is_required=data.get('is_required', True)
    )

    return JsonResponse({
        'success': True,
        'question_id': question.id,
        'order': question.order
    })


@staff_member_required
@require_http_methods(["POST"])
def update_question(request, question_id):
    """AJAX: update question"""
    question = get_object_or_404(Question, pk=question_id)
    data = json.loads(request.body)

    if 'text' in data:
        question.text = data['text']
    if 'question_type' in data:
        question.question_type = data['question_type']
    if 'order' in data:
        question.order = data['order']
    if 'is_required' in data:
        question.is_required = data['is_required']

    question.save()
    return JsonResponse({'success': True})


@staff_member_required
@require_http_methods(["POST"])
def delete_question(request, question_id):
    """AJAX: delete question"""
    question = get_object_or_404(Question, pk=question_id)
    question.delete()
    return JsonResponse({'success': True})


@staff_member_required
@require_http_methods(["POST"])
def create_option(request, question_id):
    """AJAX: create answer option"""
    question = get_object_or_404(Question, pk=question_id)
    data = json.loads(request.body)

    max_order = question.options.aggregate(Max('order'))['order__max'] or 0

    option = QuestionOption.objects.create(
        question=question,
        text=data.get('text', 'New option'),
        order=max_order + 1
    )

    return JsonResponse({
        'success': True,
        'option_id': option.id
    })


@staff_member_required
@require_http_methods(["POST"])
def update_option(request, option_id):
    """AJAX: update answer option"""
    option = get_object_or_404(QuestionOption, pk=option_id)
    data = json.loads(request.body)

    if 'text' in data:
        option.text = data['text']
    if 'order' in data:
        option.order = data['order']

    option.save()
    return JsonResponse({'success': True})


@staff_member_required
@require_http_methods(["POST"])
def delete_option(request, option_id):
    """AJAX: delete answer option"""
    option = get_object_or_404(QuestionOption, pk=option_id)
    option.delete()
    return JsonResponse({'success': True})

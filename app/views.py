from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from app.models import Question, Answer, Tag, Profile, QuestionLike, AnswerLike
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, SignupForm, QuestionForm, AnswerForm, ProfileEditForm
from django.db.models import Sum
from django.db import IntegrityError

from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST

import logging
logger = logging.getLogger(__name__)

def _handle_like_action(request, item_model, like_model, item_id_key_in_post='id', related_name_on_item='likes'):
    item_name_for_log = item_model.__name__.lower() # "question" or "answer"
    action_name_for_log = f"like_{item_name_for_log}"

    try:
        item_id = request.POST.get(item_id_key_in_post)
        val_str = request.POST.get('value')

        if not item_id or val_str not in ['1', '-1']:
            logger.warning(f"AJAX {action_name_for_log}: Bad request. {item_id_key_in_post}='{item_id}', value='{val_str}'")
            return HttpResponseBadRequest("Invalid or missing parameters.")

        val = int(val_str)
        item = get_object_or_404(item_model, pk=item_id)
        
        if not hasattr(request.user, 'profile'):
            logger.error(f"AJAX {action_name_for_log}: User {request.user.username} has no profile.")
            return JsonResponse({'error': 'User profile not found.'}, status=500)

        # Динамическое создание словаря для get_or_create
        lookup_params = {item_name_for_log: item}

        like, created = like_model.objects.get_or_create(
            author=request.user.profile,
            **lookup_params,
            defaults={'value': val}
        )

        if not created:
            if like.value != val: # Если значение изменилось, обновляем
                like.value = val
                like.save()
                logger.info(f"AJAX {action_name_for_log}: Vote changed for {item_name_for_log}_id='{item_id}' to {val} by user='{request.user.username}'")
            # Если значение не изменилось, ничего не делаем и не логируем "pass"
        else:
            logger.info(f"AJAX {action_name_for_log}: Vote created for {item_name_for_log}_id='{item_id}' with value {val} by user='{request.user.username}'")
            
        # Используем related_name_on_item для доступа к related manager (item.likes)
        total_rating = getattr(item, related_name_on_item).aggregate(Sum('value'))['value__sum'] or 0
        # Лог об успехе и новом рейтинге остается, он полезен
        logger.info(f"AJAX {action_name_for_log}: Success. {item_name_for_log}_id='{item_id}', new_rating='{total_rating}'")
        return JsonResponse({'rating': total_rating})

    except item_model.DoesNotExist:
        logger.warning(f"AJAX {action_name_for_log}: {item_model.__name__} not found. {item_id_key_in_post}='{item_id}'")
        return JsonResponse({'error': f'{item_model.__name__} not found.'}, status=404)
    except Profile.DoesNotExist: 
        logger.error(f"AJAX {action_name_for_log}: Profile for user {request.user.username} not found during operation.")
        return JsonResponse({'error': 'User profile not found.'}, status=500)
    except IntegrityError as e:
        logger.error(f"AJAX {action_name_for_log}: IntegrityError. {item_id_key_in_post}='{item_id}', value='{val_str}'. Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Database integrity error.'}, status=500)
    except Exception as e:
        logger.error(f"AJAX {action_name_for_log}: Unexpected error. {item_id_key_in_post}='{item_id}', value='{val_str}'. Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)


@login_required
@require_POST
def like_question(request):
    return _handle_like_action(request, Question, QuestionLike, 'id', 'likes')


@login_required
@require_POST
def like_answer(request):
    return _handle_like_action(request, Answer, AnswerLike, 'id', 'likes')


@login_required
@require_POST
def mark_correct(request):
    try:
        qid = request.POST.get('question')
        aid = request.POST.get('answer')
        should_be_correct_str = request.POST.get('checked', 'false') 
        should_be_correct = should_be_correct_str.lower() == 'true'

        question = get_object_or_404(Question, pk=qid)
        
        if not hasattr(request.user, 'profile'):
            logger.error(f"AJAX mark_correct: User {request.user.username} has no profile.")
            return JsonResponse({'error': 'User profile not found.'}, status=500)

        if request.user.profile != question.author:
            logger.warning(f"AJAX mark_correct: Forbidden. User '{request.user.username}' is not author of question qid='{qid}'.")
            return HttpResponseForbidden("You are not the author of this question.")
        
        answer = get_object_or_404(Answer, pk=aid, question=question)
        
        answer.is_correct = should_be_correct
        answer.save()
        
        logger.info(f"AJAX mark_correct: Success. qid='{qid}', aid='{answer.id}' set to is_correct={answer.is_correct}.")
        return JsonResponse({'answer_id': answer.id, 'is_correct': answer.is_correct})

    except Question.DoesNotExist:
        logger.warning(f"AJAX mark_correct: Question not found. qid='{qid}'")
        return JsonResponse({'error': 'Question not found.'}, status=404)
    except Answer.DoesNotExist:
        logger.warning(f"AJAX mark_correct: Answer not found. aid='{aid}' for qid='{qid}'")
        return JsonResponse({'error': 'Answer not found for this question.'}, status=404)
    except Exception as e:
        logger.error(f"AJAX mark_correct: Unexpected error. qid='{qid}', aid='{aid}'. Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)


def custom_login(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            try:
                user = form.get_user()
                login(request, user)
                if not form.cleaned_data['remember_me']:
                    request.session.set_expiry(0)
                next_url = request.GET.get('next', 'index')
                logger.info(f"User '{user.username}' logged in. Redirecting to '{next_url}'.")
                return redirect(next_url)
            except Exception as e: # Оставляем этот лог, он важен для диагностики проблем входа
                logger.error(f"Login error for attempt with username '{form.cleaned_data.get('username')}'. Error: {str(e)}", exc_info=True)
                form.add_error(None, f"Ошибка входа: {str(e)}")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})
    

def custom_signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                
                if form.cleaned_data.get('avatar'): 
                    try:
                        if hasattr(user, 'profile'):
                            user.profile.avatar = form.cleaned_data['avatar']
                            user.profile.save()
                            
                            logger.info(f"Avatar uploaded for new user '{user.username}'.")
                        else:
                            logger.error(f"Profile not found for new user '{user.username}' during avatar upload.")
                            form.add_error('avatar', "Не удалось сохранить аватар: профиль не найден.")
                            user.delete()
                            return render(request, 'register.html', {'form': form})
                    except Exception as e:
                        logger.error(f"Avatar upload error for new user '{user.username}'. Error: {str(e)}", exc_info=True)
                        form.add_error('avatar', f"Ошибка загрузки аватара: {str(e)}")
                        user.delete()
                        return render(request, 'register.html', {'form': form})
                
                login(request, user)
                logger.info(f"User '{user.username}' signed up and logged in.")
                return redirect('index')
            except Exception as e: 
                logger.error(f"Signup error. Data: {form.cleaned_data}. Error: {str(e)}", exc_info=True)
                form.add_error(None, f"Ошибка регистрации: {str(e)}")
    else:
        form = SignupForm()
    return render(request, 'register.html', {'form': form})


@login_required
def custom_logout(request):
    username = request.user.username 
    logout(request)
    logger.info(f"User '{username}' logged out.")
    return redirect(request.META.get('HTTP_REFERER', 'index'))


@login_required
def edit_profile(request):
    if not hasattr(request.user, 'profile'):
        logger.error(f"Profile edit attempt by user '{request.user.username}' who has no profile.")
        return redirect('index') 

    if request.method == 'POST':
        form = ProfileEditForm(
            request.POST, 
            request.FILES, 
            instance=request.user.profile
        )
        if form.is_valid():
            try:
                form.save()
                logger.info(f"Profile updated for user '{request.user.username}'.")
                return redirect('settings')
            except Exception as e:
                logger.error(f"Profile edit error for user '{request.user.username}'. Error: {str(e)}", exc_info=True)
                form.add_error(None, "Произошла ошибка при сохранении профиля.")
    else:
        form = ProfileEditForm(instance=request.user.profile)
    
    # Используем распаковку для добавления базового контекста
    context = {
        'form': form,
        **get_base_context() 
    }
    return render(request, 'settings.html', context)


@login_required
def ask_question(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            try:
                question = form.save(commit=False)
                
                if not hasattr(request.user, 'profile'):
                     logger.error(f"Ask question attempt by user '{request.user.username}' who has no profile.")
                     form.add_error(None, "Не удалось создать вопрос: профиль пользователя не найден.")
                else:
                    question.author = request.user.profile
                    question.save() 
                    
                    tags_string = form.cleaned_data.get('tags', '')
                    if tags_string:
                        tag_names = [t.strip() for t in tags_string.split(',') if t.strip()]
                        for tag_name in tag_names:
                            tag, _ = Tag.objects.get_or_create(name=tag_name)
                            question.tags.add(tag)
                    
                    logger.info(f"New question (id={question.id}) asked by '{request.user.username}'. Title: '{question.title}'.")
                    return redirect('question', question_id=question.id)
            except Exception as e:
                logger.error(f"Error asking question by user '{request.user.username}'. Data: {form.cleaned_data}. Error: {str(e)}", exc_info=True)
                form.add_error(None, f"Ошибка создания вопроса: {str(e)}")
    else:
        form = QuestionForm()
    
    context = {
        'form': form,
        **get_base_context()
    }
    return render(request, 'ask.html', context)


def question_detail(request, question_id): 
    question = get_object_or_404(Question, pk=question_id)
    answers_qs = Answer.objects.filter(question=question).select_related('author', 'author__user').order_by('-created_at')
    
    answer_form = AnswerForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            logger.info(f"Unauthenticated user tried to post answer to question_id='{question_id}'. Redirecting to login.")
            return redirect(f"{reverse('login')}?next={request.get_full_path()}")
            
        answer_form = AnswerForm(request.POST)
        if answer_form.is_valid():
            if not hasattr(request.user, 'profile'):
                logger.error(f"Post answer attempt by user '{request.user.username}' who has no profile. question_id='{question_id}'")
                answer_form.add_error(None, "Не удалось добавить ответ: профиль пользователя не найден.")
            else:
                answer = answer_form.save(commit=False)
                answer.question = question
                answer.author = request.user.profile
                answer.save()
                logger.info(f"New answer (id={answer.id}) posted by '{request.user.username}' to question_id='{question_id}'.")
                return redirect(f"{reverse('question', args=[question.id])}#answer-{answer.id}")
        else:
            logger.warning(f"Invalid answer form for question_id='{question_id}'. Errors: {answer_form.errors.as_json()}")

    answers_page = paginate(answers_qs, request, 5)
    
    context = {
        'question': question,
        'answers': answers_page, 
        'answer_form': answer_form,
        **get_base_context()
    }
    return render(request, 'question.html', context)


def paginate(objects_list, request, per_page=10):
    paginator = Paginator(objects_list, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    
    return page


def get_base_context():
    popular_tags = Tag.objects.most_popular()
    new_users = Profile.objects.newest()
    return {
        'popular_tags': popular_tags,
        'new_users': new_users,
    }


def index(request):
    questions_qs = Question.objects.new().select_related('author', 'author__user').prefetch_related('tags')
    page_obj = paginate(questions_qs, request, 10) 
    context = {
        'questions': page_obj, 
        'section': 'new',
        **get_base_context()
    }
    return render(request, 'index.html', context)


def hot(request):
    questions_qs = Question.objects.hot().select_related('author', 'author__user').prefetch_related('tags')
    page_obj = paginate(questions_qs, request, 10)
    context = {
        'questions': page_obj,
        'section': 'hot',
        **get_base_context()
    }
    return render(request, 'index.html', context)


def tag(request, tag_name):
    tag_obj = get_object_or_404(Tag, name=tag_name) 
    questions_qs = Question.objects.by_tag(tag_name).select_related('author', 'author__user').prefetch_related('tags')
    page_obj = paginate(questions_qs, request, 5)
    context = {
        'questions': page_obj,
        'tag': tag_name, 
        'section': 'tag',
        **get_base_context()
    }
    return render(request, 'index.html', context)
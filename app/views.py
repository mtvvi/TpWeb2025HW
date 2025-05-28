from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from app.models import Question, Answer, Tag, Profile, QuestionLike, AnswerLike # Убедитесь, что все модели импортированы
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
# from django.shortcuts import redirect # уже импортирован выше
from .forms import LoginForm, SignupForm, QuestionForm, AnswerForm, ProfileEditForm
from django.db.models import Count, Sum
from django.db import IntegrityError # Импортируем для явного отлова

from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST
# from django.contrib.auth.decorators import login_required # уже импортирован выше

# --- НАЧАЛО: Определение логгера ---
import logging
logger = logging.getLogger(__name__) # Определяем логгер для этого модуля
# --- КОНЕЦ: Определение логгера ---


@login_required
@require_POST
def like_question(request):
    try:
        qid = request.POST.get('id')
        val_str = request.POST.get('value')

        logger.debug(f"AJAX like_question: user='{request.user.username}', qid='{qid}', value='{val_str}'")

        if not qid or val_str not in ['1', '-1']:
            logger.warning(f"AJAX like_question: Bad request. qid='{qid}', value='{val_str}'")
            return HttpResponseBadRequest("Invalid or missing parameters.")

        val = int(val_str)
        question = get_object_or_404(Question, pk=qid)
        
        if not hasattr(request.user, 'profile'):
            logger.error(f"AJAX like_question: User {request.user.username} has no profile.")
            return JsonResponse({'error': 'User profile not found.'}, status=500)

        like, created = QuestionLike.objects.get_or_create(
            author=request.user.profile,
            question=question,
            defaults={'value': val}
        )

        if not created:
            if like.value == val:
                
                pass 
            else: 
                like.value = val
                like.save()
                logger.info(f"AJAX like_question: Vote changed for qid='{qid}' to {val} by user='{request.user.username}'")
        else:
            logger.info(f"AJAX like_question: Vote created for qid='{qid}' with value {val} by user='{request.user.username}'")
            
        total_rating = question.likes.aggregate(Sum('value'))['value__sum'] or 0
        logger.info(f"AJAX like_question: Success. qid='{qid}', new_rating='{total_rating}'")
        return JsonResponse({'rating': total_rating})

    except Question.DoesNotExist:
        logger.warning(f"AJAX like_question: Question not found. qid='{qid}'")
        return JsonResponse({'error': 'Question not found.'}, status=404)
    except Profile.DoesNotExist: 
        logger.error(f"AJAX like_question: Profile for user {request.user.username} not found during operation.")
        return JsonResponse({'error': 'User profile not found.'}, status=500)
    except IntegrityError as e:
        logger.error(f"AJAX like_question: IntegrityError. qid='{qid}', value='{val_str}'. Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Database integrity error.'}, status=500)
    except Exception as e:
        logger.error(f"AJAX like_question: Unexpected error. qid='{qid}', value='{val_str}'. Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)

@login_required
@require_POST
def like_answer(request):
    try:
        aid = request.POST.get('id')
        val_str = request.POST.get('value')

        logger.debug(f"AJAX like_answer: user='{request.user.username}', aid='{aid}', value='{val_str}'")

        if not aid or val_str not in ['1', '-1']:
            logger.warning(f"AJAX like_answer: Bad request. aid='{aid}', value='{val_str}'")
            return HttpResponseBadRequest("Invalid or missing parameters.")
        
        val = int(val_str)
        answer = get_object_or_404(Answer, pk=aid)

        if not hasattr(request.user, 'profile'):
            logger.error(f"AJAX like_answer: User {request.user.username} has no profile.")
            return JsonResponse({'error': 'User profile not found.'}, status=500)

        like, created = AnswerLike.objects.get_or_create(
            author=request.user.profile,
            answer=answer,
            defaults={'value': val}
        )

        if not created:
            if like.value == val:
                pass
            else:
                like.value = val
                like.save()
                logger.info(f"AJAX like_answer: Vote changed for aid='{aid}' to {val} by user='{request.user.username}'")
        else:
            logger.info(f"AJAX like_answer: Vote created for aid='{aid}' with value {val} by user='{request.user.username}'")
        
        total_rating = answer.likes.aggregate(Sum('value'))['value__sum'] or 0
        logger.info(f"AJAX like_answer: Success. aid='{aid}', new_rating='{total_rating}'")
        return JsonResponse({'rating': total_rating})

    except Answer.DoesNotExist:
        logger.warning(f"AJAX like_answer: Answer not found. aid='{aid}'")
        return JsonResponse({'error': 'Answer not found.'}, status=404)
    except Profile.DoesNotExist:
        logger.error(f"AJAX like_answer: Profile for user {request.user.username} not found during operation.")
        return JsonResponse({'error': 'User profile not found.'}, status=500)
    except IntegrityError as e:
        logger.error(f"AJAX like_answer: IntegrityError. aid='{aid}', value='{val_str}'. Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Database integrity error.'}, status=500)
    except Exception as e:
        logger.error(f"AJAX like_answer: Unexpected error. aid='{aid}', value='{val_str}'. Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)

# views.py (функция mark_correct)

@login_required
@require_POST
def mark_correct(request):
    try:
        qid = request.POST.get('question')
        aid = request.POST.get('answer')
        # Новый параметр, указывающий, нужно установить или снять отметку
        should_be_correct_str = request.POST.get('checked', 'false') # 'true' или 'false'
        should_be_correct = should_be_correct_str.lower() == 'true'


        logger.debug(f"AJAX mark_correct: user='{request.user.username}', qid='{qid}', aid='{aid}', checked='{should_be_correct}'")

        question = get_object_or_404(Question, pk=qid)
        
        if not hasattr(request.user, 'profile'):
            logger.error(f"AJAX mark_correct: User {request.user.username} has no profile.")
            return JsonResponse({'error': 'User profile not found.'}, status=500)

        if request.user.profile != question.author:
            logger.warning(f"AJAX mark_correct: Forbidden. User '{request.user.username}' is not author of question qid='{qid}'.")
            return HttpResponseForbidden("You are not the author of this question.")
        
        answer = get_object_or_404(Answer, pk=aid, question=question)
        
        # Просто устанавливаем или снимаем флаг для этого ответа
        answer.is_correct = should_be_correct
        answer.save()
        
        logger.info(f"AJAX mark_correct: Success. qid='{qid}', aid='{answer.id}' set to is_correct={answer.is_correct}.")
        # Возвращаем ID ответа и его новое состояние
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
            except Exception as e:
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
                            # Этого не должно произойти, если сигнал работает
                            logger.error(f"Profile not found for new user '{user.username}' during avatar upload.")
                            form.add_error('avatar', "Не удалось сохранить аватар: профиль не найден.")
                            user.delete() # Откат, если профиль не создался и аватар важен
                            return render(request, 'register.html', {'form': form})
                    except Exception as e:
                        logger.error(f"Avatar upload error for new user '{user.username}'. Error: {str(e)}", exc_info=True)
                        form.add_error('avatar', f"Ошибка загрузки аватара: {str(e)}")
                        user.delete()
                        return render(request, 'register.html', {'form': form})
                
                login(request, user)
                logger.info(f"User '{user.username}' signed up and logged in.")
                return redirect('index')
            except Exception as e: # Общий отлов ошибок при регистрации
                logger.error(f"Signup error. Data: {form.cleaned_data}. Error: {str(e)}", exc_info=True)
                form.add_error(None, f"Ошибка регистрации: {str(e)}")
    else:
        form = SignupForm()
    return render(request, 'register.html', {'form': form})

@login_required
def custom_logout(request):
    username = request.user.username # Сохраняем имя пользователя для лога перед выходом
    logout(request)
    logger.info(f"User '{username}' logged out.")
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def edit_profile(request):
    if not hasattr(request.user, 'profile'):
        # Этого не должно случиться для аутентифицированного пользователя, если сигналы работают
        logger.error(f"Profile edit attempt by user '{request.user.username}' who has no profile.")
        # Можно показать сообщение об ошибке или редирект
        return redirect('index') # Или на страницу с сообщением об ошибке

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
    
    context = {
        'form': form,
    }
    context.update(get_base_context()) # Добавляем базовый контекст
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
                    question.save() # Сначала сохраняем вопрос, чтобы получить ID
                    
                    tags_string = form.cleaned_data.get('tags', '')
                    if tags_string:
                        tag_names = [t.strip() for t in tags_string.split(',') if t.strip()]
                        for tag_name in tag_names:
                            tag, _ = Tag.objects.get_or_create(name=tag_name)
                            question.tags.add(tag)
                    
                    logger.info(f"New question (id={question.id}) asked by '{request.user.username}'. Title: '{question.title}'.")
                    return redirect('question', question_id=question.id) # Используем question_id
            except Exception as e:
                logger.error(f"Error asking question by user '{request.user.username}'. Data: {form.cleaned_data}. Error: {str(e)}", exc_info=True)
                form.add_error(None, f"Ошибка создания вопроса: {str(e)}")
            
    else:
        form = QuestionForm()
    
    context = {
        'form': form,
    }
    context.update(get_base_context()) # Добавляем базовый контекст
    return render(request, 'ask.html', context)


def question_detail(request, question_id): # Это представление было 'question' в вашем urls.py
    question = get_object_or_404(Question, pk=question_id) # pk= или id=
    # Загружаем ответы, связанные с автором и сортируем (например, по рейтингу или дате)
    # .select_related('author__user') чтобы получить и профиль и пользователя
    answers_qs = Answer.objects.filter(question=question).select_related('author', 'author__user').order_by('-created_at') # или '-rating' и т.д.
    
    answer_form = AnswerForm() # Инициализируем форму здесь для GET запросов

    if request.method == 'POST':
        if not request.user.is_authenticated:
            logger.info(f"Unauthenticated user tried to post answer to question_id='{question_id}'. Redirecting to login.")
            return redirect(f"{reverse('login')}?next={request.get_full_path()}") # Используем get_full_path
            
        answer_form = AnswerForm(request.POST) # Пересоздаем форму с POST данными
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


    # Пагинация ответов для GET запроса
    answers_page = paginate(answers_qs, request, 5) # 5 - количество ответов на странице
    
    context = {
        'question': question,
        'answers': answers_page, # Передаем объект страницы пагинации
        # 'page_obj': answers_page, # 'answers' уже является page_obj
        'answer_form': answer_form, # Передаем форму ответа
    }
    context.update(get_base_context())
    return render(request, 'question.html', context)

def paginate(objects_list, request, per_page=10):
    paginator = Paginator(objects_list, per_page)
    page_number = request.GET.get('page', 1) # По умолчанию первая страница
    
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    
    return page

def get_base_context():
    # Эти данные нужны на многих страницах, выносим в отдельную функцию
    popular_tags = Tag.objects.most_popular()
    new_users = Profile.objects.newest()
    return {
        'popular_tags': popular_tags,
        'new_users': new_users,
    }

def index(request):

    questions_qs = Question.objects.new().select_related('author', 'author__user').prefetch_related('tags')
    page_obj = paginate(questions_qs, request, 10) # Используем page_obj для единообразия
    context = {
        'questions': page_obj, 
        # 'page_obj': page_obj, # 'questions' уже является page_obj
        'section': 'new'
    }
    context.update(get_base_context())
    return render(request, 'index.html', context)

def hot(request):
    questions_qs = Question.objects.hot().select_related('author', 'author__user').prefetch_related('tags')
    page_obj = paginate(questions_qs, request, 10)
    context = {
        'questions': page_obj,
        # 'page_obj': page_obj,
        'section': 'hot'
    }
    context.update(get_base_context())
    return render(request, 'index.html', context)

def tag(request, tag_name):
    tag_obj = get_object_or_404(Tag, name=tag_name) 
    questions_qs = Question.objects.by_tag(tag_name).select_related('author', 'author__user').prefetch_related('tags')
    page_obj = paginate(questions_qs, request, 5) # Другое количество на странице для тегов
    context = {
        'questions': page_obj,
        # 'page_obj': page_obj,
        'tag': tag_name, # Передаем имя тега (можно и tag_obj)
        'section': 'tag'
    }
    context.update(get_base_context())
    return render(request, 'index.html', context)
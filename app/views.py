from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from app.models import Question, Answer, Tag, Profile
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .forms import LoginForm, SignupForm, QuestionForm, AnswerForm, ProfileEditForm

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
                return redirect(next_url)
            except Exception as e:
                form.add_error(None, f"Ошибка входа: {str(e)}")
        # Ошибки формы уже содержатся в form.errors
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})
    

def custom_signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                if form.cleaned_data['avatar']:
                    try:
                        user.profile.avatar = form.cleaned_data['avatar']
                        user.profile.save()
                    except Exception as e:
                        form.add_error('avatar', f"Ошибка загрузки аватара: {str(e)}")
                        user.delete()  # Откатываем создание пользователя
                        return render(request, 'register.html', {'form': form})
                
                login(request, user)
                return redirect('index')
            except Exception as e:
                form.add_error(None, f"Ошибка регистрации: {str(e)}")
    else:
        form = SignupForm()
    return render(request, 'register.html', {'form': form})

@login_required
def custom_logout(request):
    logout(request)
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileEditForm(
            request.POST, 
            request.FILES, 
            instance=request.user.profile
        )
        if form.is_valid():
            form.save()
            return redirect('settings')
    else:
        form = ProfileEditForm(instance=request.user.profile)
    
    context = {
        'form': form,
        'popular_tags': Tag.objects.most_popular(),
        'new_users': Profile.objects.newest()
    }
    return render(request, 'settings.html', context)

@login_required
def ask_question(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            try:
                question = form.save(commit=False)
                question.author = request.user.profile
                question.save()
                
                tags = [t.strip() for t in form.cleaned_data['tags'].split(',')]
                for tag_name in tags:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    question.tags.add(tag)
                    
                return redirect('question', question_id=question.id)
            except Exception as e:
                form.add_error(None, f"Ошибка загрузки: {str(e)}")
            
    else:
        form = QuestionForm()
    
    context = {
        'form': form,
        'popular_tags': Tag.objects.most_popular(),
        'new_users': Profile.objects.newest()
    }
    return render(request, 'ask.html', context)

def question_detail(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    answers = Answer.objects.filter(question=question).select_related('author')
    answers_page = paginate(answers, request, 10)
    
    if request.method == 'POST':
        answer_form = AnswerForm(request.POST)
        if answer_form.is_valid():
            answer = answer_form.save(commit=False)
            answer.question = question
            answer.author = request.user.profile
            answer.save()
            return redirect(f"{reverse('question', args=[question.id])}#answer-{answer.id}")
    else:
        answer_form = AnswerForm()
    
    context = {
        'question': question,
        'answers': answers_page,
        'page_obj': answers_page,
        'answer_form': answer_form,
    }
    context.update(get_base_context())
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
    questions = Question.objects.new().prefetch_related('tags')
    page = paginate(questions, request, 10)
    context = {
        'questions': page,
        'page_obj': page,
        'section': 'new'
    }
    context.update(get_base_context())
    return render(request, 'index.html', context)

def hot(request):
    questions = Question.objects.hot().prefetch_related('tags')
    page = paginate(questions, request, 10)
    context = {
        'questions': page,
        'page_obj': page,
        'section': 'hot'
    }
    context.update(get_base_context())
    return render(request, 'index.html', context)

def tag(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    questions = Question.objects.by_tag(tag_name).prefetch_related('tags')
    page = paginate(questions, request, 5)
    context = {
        'questions': page,
        'page_obj': page,
        'tag': tag_name,
        'section': 'tag'
    }
    context.update(get_base_context())
    return render(request, 'index.html', context)

def question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    answers = Answer.objects.filter(question=question).order_by('-created_at')
    
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
            
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.question = question
            answer.author = request.user.profile
            answer.save()
            # Редирект на первый элемент пагинации с якорем
            return redirect(f"{reverse('question', args=[question.id])}?page=1#answer-{answer.id}")
    else:
        form = AnswerForm()
    
    paginator = Paginator(answers, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'question': question,
        'answers': page_obj,
        'form': form,
    }
    return render(request, 'question.html', context)
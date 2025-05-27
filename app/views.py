from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404
from app.models import Question, Answer, Tag, Profile

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
    question = get_object_or_404(Question.objects.prefetch_related('tags'), id=question_id)
    answers = Answer.objects.filter(question=question).select_related('author')
    answers_page = paginate(answers, request, per_page=5)
    context = {
        'question': question,
        'answers': answers_page,
        'page_obj': answers_page,
    }
    context.update(get_base_context())
    return render(request, 'question.html', context)

def login(request):
    return render(request, 'login.html')

def signup(request):
    return render(request, 'register.html')

def ask(request):
    return render(request, 'ask.html')

def settings(request):
    return render(request, 'user.html')
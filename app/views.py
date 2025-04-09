from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render

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

def generate_answers(question_id):
    return [
        {
            'id': i,
            'text': f'This is answer {i} to question {question_id}. It provides a detailed solution to the problem mentioned above.',
            'correct': i == 1,
            'rating': i * 3 - 7,
            'author': f'User{i}',
        }
        for i in range(1, 15)
    ]

def index(request):
    questions = []
    for i in range(1, 100):
        answers = generate_answers(i)
        questions.append({
            'title': f'New question {i}',
            'id': i,
            'text': f'New question text {i}',
            'answers': len(answers),  
            'tags': ['Django', 'Python'],
            'rating': i * 3 - 7, 
        })
    page = paginate(questions, request, 10)
    return render(request, 'index.html', {'questions': page})


def hot(request):
    questions = []
    for i in range(1, 100):
        questions.append({
            'title': f'Hot question {i}',
            'id': i,
            'text': f'Hot question text {i}',
            'answers': i % 5,
        })
    
    page = paginate(questions, request, 10)
    return render(request, 'index.html', {'questions': page})

def tag(request, tag_name):
    questions = []
    for i in range(1, 15):
        questions.append({
            'title': f'Question about {tag_name} {i}',
            'id': i,
            'text': f'Question text about {tag_name} {i}',
            'answers': i % 5,
        })
    
    page = paginate(questions, request, 5)
    return render(request, 'index.html', {'questions': page, 'tag': tag_name})

def question(request, question_id):
    answers = generate_answers(question_id)
    context = {
        'question': {
            'id': question_id,
            'title': f'Sample Question {question_id}',
            'text': 'This is the main question content.',
            'tags': ['Django', 'Python'],
            'rating': question_id * 3 - 7,
        },
        'answers': answers,
    }
    return render(request, 'question.html', context)




def login(request):
    return render(request, 'login.html')

def signup(request):
    return render(request, 'register.html')

def ask(request):
    return render(request, 'ask.html')

def settings(request):
    return render(request, 'user.html')
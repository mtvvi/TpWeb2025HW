import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from faker import Faker
from app.models import Profile, Tag, Question, Answer, QuestionLike, AnswerLike


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('ratio', type=int)

    def handle(self, *args, **options):
        ratio = options['ratio']
        fake = Faker()
        Faker.seed(0)
        random.seed(0)

        # Пользователи и профили
        pw_hash = make_password('password')
        users = [
            User(username=f'fake_user_{i}', email=f'fake_{i}@faker.com', password=pw_hash)
            for i in range(ratio)
        ]
        User.objects.bulk_create(users)
        users = list(User.objects.filter(username__startswith='fake_user_').order_by('-id')[:ratio])

        profiles = [Profile(user=user) for user in users]
        Profile.objects.bulk_create(profiles)
        profiles = list(Profile.objects.filter(user__in=users))

        self.stdout.write(self.style.SUCCESS(f'Создано {len(users)} пользователей и профилей'))

        # Псевдо-фейковые уникальные теги
        tags = [Tag(name=f'tag_{i}') for i in range(ratio)]
        Tag.objects.bulk_create(tags)
        tags = list(Tag.objects.filter(name__startswith='tag_').order_by('-id')[:ratio])
        self.stdout.write(self.style.SUCCESS(f'Создано {len(tags)} тэгов'))

        # Вопросы
        questions = [
            Question(
                title=fake.sentence(nb_words=6),
                text=fake.text(max_nb_chars=200),
                author=random.choice(profiles),
            ) for _ in range(ratio * 10)
        ]
        Question.objects.bulk_create(questions)
        questions = list(Question.objects.order_by('-id')[:len(questions)])

        # Теги к вопросам
        through_model = Question.tags.through
        q_tag_links = [
            through_model(question_id=q.id, tag_id=t.id)
            for q in questions
            for t in random.sample(tags, k=random.randint(1, 3))
        ]
        through_model.objects.bulk_create(q_tag_links, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f'Создано {len(questions)} вопросов и прикреплены тэги'))

        # Ответы
        answers = [
            Answer(
                text=fake.text(max_nb_chars=150),
                question=random.choice(questions),
                author=random.choice(profiles),
                is_correct=random.choice([True, False, False]),
            ) for _ in range(ratio * 100)
        ]
        Answer.objects.bulk_create(answers)
        answers = list(Answer.objects.order_by('-id')[:len(answers)])
        self.stdout.write(self.style.SUCCESS(f'Создано {len(answers)} ответов'))

        # Лайки
        def generate_likes(model_cls, item_field, items, count):
            seen = set()
            objs = []

            while len(objs) < count:
                profile = random.choice(profiles)
                item = random.choice(items)
                key = (profile.id, item.id)
                if key in seen:
                    continue
                seen.add(key)
                kwargs = {
                    'author': profile,
                    item_field: item,
                    'value': random.choice([1, -1])
                }
                objs.append(model_cls(**kwargs))
            return objs

        qlikes = generate_likes(QuestionLike, 'question', questions, ratio * 100)
        alikes = generate_likes(AnswerLike, 'answer', answers, ratio * 100)

        QuestionLike.objects.bulk_create(qlikes, ignore_conflicts=True)
        AnswerLike.objects.bulk_create(alikes, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(
            f'Создано {len(qlikes)} лайков вопросов и {len(alikes)} лайков ответов'
        ))
        self.stdout.write(self.style.SUCCESS('Заполнение базы завершено!'))

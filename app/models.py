from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count, Sum

class ProfileManager(models.Manager):
    def newest(self):
        return self.order_by('created_at').all()[:10]

class Profile(models.Model):
    objects = ProfileManager()
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(default='img/Cover.jpg', upload_to='avatars/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


class TagManager(models.Manager):
    def most_popular(self):
        return self.annotate(quest_count=Count('questions')).order_by('-quest_count')[:10]

class Tag(models.Model):
    objects = TagManager()
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name

class QuestionManager(models.Manager):
    def hot(self):
        return self.annotate(
            rating_sum=Sum('likes__value'),
            answers_count=Count('answers', distinct=True)
        ).order_by('-answers_count', '-created_at', '-rating_sum')
    
    def new(self):
        return self.order_by('-created_at')
    
    def by_tag(self, tag_name):
        return self.filter(tags__name=tag_name).order_by('-created_at')

class Question(models.Model):
    objects = QuestionManager()
    title = models.CharField(max_length=255)
    text = models.TextField()
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='questions')
    tags = models.ManyToManyField(Tag, related_name='questions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def rating(self):
        return self.likes.aggregate(Sum('value'))['value__sum'] or 0

    def answers_count(self):
        return self.answers.count()

    def get_tags(self):
        return list(self.tags.values_list('name', flat=True))

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['created_at']

class Answer(models.Model):
    text = models.TextField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='answers')
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def rating(self):
        return self.likes.aggregate(Sum('value'))['value__sum'] or 0

    def get_author_name(self):
        return self.author.user.username

    def __str__(self):
        return self.text

    class Meta:
        ordering = ['created_at']

class QuestionLike(models.Model):
    LIKE_CHOICES = (
        (1, 'Like'),
        (-1, 'Dislike')
    )
    
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='question_likes')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='likes')
    value = models.SmallIntegerField(choices=LIKE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['author', 'question']


class AnswerLike(models.Model):
    LIKE_CHOICES = (
        (1, 'Like'),
        (-1, 'Dislike')
    )
    
    author = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='answer_likes')
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='likes')
    value = models.SmallIntegerField(choices=LIKE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['author', 'answer']

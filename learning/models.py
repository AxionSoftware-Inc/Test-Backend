from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Subject(TimestampedModel):
    title = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.title


class Topic(TimestampedModel):
    subject = models.ForeignKey(Subject, related_name="topics", on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    slug = models.SlugField()
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("subject", "slug")

    def __str__(self) -> str:
        return f"{self.subject.title} / {self.title}"


class Skill(TimestampedModel):
    topic = models.ForeignKey(Topic, related_name="skills", on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    slug = models.SlugField()
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("topic", "slug")

    def __str__(self) -> str:
        return self.title


class Question(TimestampedModel):
    class QuestionType(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Single choice"
        MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
        SHORT_ANSWER = "short_answer", "Short answer"

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    subject = models.ForeignKey(Subject, related_name="questions", on_delete=models.PROTECT)
    topic = models.ForeignKey(Topic, related_name="questions", on_delete=models.PROTECT)
    skills = models.ManyToManyField(Skill, related_name="questions", blank=True)
    type = models.CharField(max_length=32, choices=QuestionType.choices)
    difficulty = models.CharField(max_length=32, choices=Difficulty.choices)
    prompt = models.TextField()
    options = models.JSONField(default=list, blank=True)
    answer = models.CharField(max_length=255, blank=True)
    explanation = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.prompt[:80]


class Test(TimestampedModel):
    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    subject = models.ForeignKey(Subject, related_name="tests", on_delete=models.PROTECT)
    topic = models.ForeignKey(Topic, related_name="tests", on_delete=models.PROTECT)
    difficulty = models.CharField(max_length=32, choices=Question.Difficulty.choices)
    estimated_minutes = models.PositiveIntegerField(default=10)
    passing_score = models.PositiveIntegerField(default=70)
    questions = models.ManyToManyField(Question, through="TestQuestion", related_name="tests")

    def __str__(self) -> str:
        return self.title


class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("test", "question")
        ordering = ["order", "id"]


class TestSession(TimestampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    test = models.ForeignKey(Test, related_name="sessions", on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.IN_PROGRESS)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.test.title} / {self.status}"


class Answer(TimestampedModel):
    session = models.ForeignKey(TestSession, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE)
    value = models.TextField(blank=True)
    is_flagged = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "question")


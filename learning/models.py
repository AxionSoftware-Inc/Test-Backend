from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class RoleProfile(TimestampedModel):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        SCHOOL = "school", "School"
        CREATOR = "creator", "Creator"
        ADMIN = "admin", "Admin"

    identity_code = models.CharField(max_length=120, unique=True)
    display_name = models.CharField(max_length=160, blank=True)
    active_role = models.CharField(max_length=24, choices=Role.choices, default=Role.STUDENT)
    available_roles = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        if not self.available_roles:
            self.available_roles = [choice[0] for choice in self.Role.choices]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.identity_code} / {self.active_role}"


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
    class PublishStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    subject = models.ForeignKey(Subject, related_name="tests", on_delete=models.PROTECT)
    topic = models.ForeignKey(Topic, related_name="tests", on_delete=models.PROTECT)
    difficulty = models.CharField(max_length=32, choices=Question.Difficulty.choices)
    estimated_minutes = models.PositiveIntegerField(default=10)
    passing_score = models.PositiveIntegerField(default=70)
    status = models.CharField(max_length=24, choices=PublishStatus.choices, default=PublishStatus.PUBLISHED)
    creator_name = models.CharField(max_length=160, blank=True)
    creator_code = models.CharField(max_length=80, blank=True)
    manage_key = models.CharField(max_length=80, blank=True)
    questions = models.ManyToManyField(Question, through="TestQuestion", related_name="tests")

    def __str__(self) -> str:
        return self.title


class TeacherClass(TimestampedModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    teacher_name = models.CharField(max_length=160)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC)
    join_code = models.CharField(max_length=32, blank=True)
    manage_code = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class ClassStudent(TimestampedModel):
    classroom = models.ForeignKey(TeacherClass, related_name="students", on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    student_code = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = ("classroom", "student_code")

    def __str__(self) -> str:
        return self.name


class ClassTestAssignment(TimestampedModel):
    classroom = models.ForeignKey(TeacherClass, related_name="assignments", on_delete=models.CASCADE)
    test = models.ForeignKey(Test, related_name="class_assignments", on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class ExamPack(TimestampedModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    exam_type = models.CharField(max_length=80, blank=True)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC)
    access_code = models.CharField(max_length=32, blank=True)
    manage_code = models.CharField(max_length=80, blank=True)
    price_label = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class ExamPackItem(TimestampedModel):
    pack = models.ForeignKey(ExamPack, related_name="items", on_delete=models.CASCADE)
    test = models.ForeignKey(Test, related_name="exam_pack_items", on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("pack", "test")

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
    classroom = models.ForeignKey(TeacherClass, null=True, blank=True, related_name="sessions", on_delete=models.SET_NULL)
    assignment = models.ForeignKey(ClassTestAssignment, null=True, blank=True, related_name="sessions", on_delete=models.SET_NULL)
    exam_pack = models.ForeignKey(ExamPack, null=True, blank=True, related_name="sessions", on_delete=models.SET_NULL)
    exam_pack_item = models.ForeignKey(ExamPackItem, null=True, blank=True, related_name="sessions", on_delete=models.SET_NULL)
    student_name = models.CharField(max_length=160, blank=True)
    student_code = models.CharField(max_length=80, blank=True)
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

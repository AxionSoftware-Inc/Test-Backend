from django.db.models import Count
from django.utils import timezone
from rest_framework import decorators, response, status, viewsets

from learning.models import Answer, Question, Skill, Subject, Test, TestSession, Topic
from learning.serializers import (
    AnswerSerializer,
    QuestionSerializer,
    SkillSerializer,
    SubjectSerializer,
    TestSerializer,
    TestSessionSerializer,
    TopicSerializer,
)


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by("title")
    serializer_class = SubjectSerializer
    lookup_field = "slug"

    @decorators.action(detail=True, methods=["get"])
    def topics(self, request, slug=None):
        subject = self.get_object()
        topics = (
            Topic.objects.filter(subject=subject)
            .annotate(test_count=Count("tests", distinct=True))
            .order_by("title")
        )
        return response.Response(TopicSerializer(topics, many=True).data)


class TopicViewSet(viewsets.ModelViewSet):
    queryset = (
        Topic.objects.select_related("subject")
        .annotate(test_count=Count("tests", distinct=True))
        .all()
        .order_by("subject__title", "title")
    )
    serializer_class = TopicSerializer
    lookup_field = "slug"

    def get_queryset(self):
        queryset = super().get_queryset()
        subject = self.request.query_params.get("subject")
        return queryset.filter(subject__slug=subject) if subject else queryset

    @decorators.action(detail=True, methods=["get"])
    def levels(self, request, slug=None):
        topic = self.get_object()
        data = []
        for difficulty, label in Question.Difficulty.choices:
            tests = Test.objects.filter(topic=topic, difficulty=difficulty)
            data.append(
                {
                    "difficulty": difficulty,
                    "label": label,
                    "test_count": tests.count(),
                    "tests": TestSerializer(tests, many=True).data,
                }
            )
        return response.Response(data)

    @decorators.action(detail=True, methods=["get"])
    def tests(self, request, slug=None):
        topic = self.get_object()
        queryset = Test.objects.filter(topic=topic).select_related("subject", "topic")
        difficulty = request.query_params.get("difficulty")
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        return response.Response(TestSerializer(queryset, many=True).data)


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.select_related("topic").all().order_by("topic__title", "title")
    serializer_class = SkillSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.select_related("subject", "topic").prefetch_related("skills").all().order_by("-id")
    serializer_class = QuestionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = {
            "subject__slug": self.request.query_params.get("subject"),
            "topic__slug": self.request.query_params.get("topic"),
            "difficulty": self.request.query_params.get("difficulty"),
            "type": self.request.query_params.get("type"),
        }
        return queryset.filter(**{key: value for key, value in filters.items() if value})


class TestViewSet(viewsets.ModelViewSet):
    queryset = (
        Test.objects.select_related("subject", "topic")
        .prefetch_related("testquestion_set__question__skills")
        .all()
        .order_by("topic__title", "difficulty", "title")
    )
    serializer_class = TestSerializer
    lookup_field = "slug"

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = {
            "subject__slug": self.request.query_params.get("subject"),
            "topic__slug": self.request.query_params.get("topic"),
            "difficulty": self.request.query_params.get("difficulty"),
        }
        return queryset.filter(**{key: value for key, value in filters.items() if value})

    @decorators.action(detail=True, methods=["post"])
    def start(self, request, slug=None):
        test = self.get_object()
        session = TestSession.objects.create(test=test, user=request.user if request.user.is_authenticated else None)
        return response.Response(TestSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class TestSessionViewSet(viewsets.ModelViewSet):
    queryset = TestSession.objects.select_related("test", "user").prefetch_related("answers").all().order_by("-created_at")
    serializer_class = TestSessionSerializer

    @decorators.action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        session = self.get_object()
        serializer = AnswerSerializer(data={**request.data, "session": session.id})
        serializer.is_valid(raise_exception=True)
        Answer.objects.update_or_create(
            session=session,
            question=serializer.validated_data["question"],
            defaults={
                "value": serializer.validated_data.get("value", ""),
                "is_flagged": serializer.validated_data.get("is_flagged", False),
            },
        )
        return response.Response(TestSessionSerializer(session).data)

    @decorators.action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        session = self.get_object()
        session.status = TestSession.Status.SUBMITTED
        session.submitted_at = timezone.now()
        session.save(update_fields=["status", "submitted_at", "updated_at"])
        return response.Response(TestSessionSerializer(session).data)

from django.db.models import Count
from django.utils import timezone
from rest_framework import decorators, response, status, viewsets

from learning.models import Answer, Question, Skill, Subject, Test, TestSession, Topic
from learning.serializers import (
    AnswerSerializer,
    CreateTestSerializer,
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

    def get_serializer_class(self):
        return CreateTestSerializer if self.action == "create" else TestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.save()
        return response.Response(TestSerializer(test).data, status=status.HTTP_201_CREATED)

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


@decorators.api_view(["GET"])
def profile_summary(request):
    sessions = (
        TestSession.objects.select_related("test", "test__topic", "test__subject")
        .prefetch_related("answers", "test__testquestion_set__question")
        .order_by("-created_at")
    )
    submitted_sessions = [session for session in sessions if session.status == TestSession.Status.SUBMITTED]

    recent_tests = []
    topic_totals = {}
    weekly_activity = {}
    correct_total = 0
    question_total = 0

    for session in submitted_sessions:
        questions = [item.question for item in session.test.testquestion_set.all()]
        answer_map = {answer.question_id: answer.value.strip() for answer in session.answers.all()}
        correct = sum(1 for question in questions if answer_map.get(question.id, "") == question.answer.strip())
        total = len(questions)
        percent = round((correct / total) * 100) if total else 0
        correct_total += correct
        question_total += total

        topic_slug = session.test.topic.slug
        topic_data = topic_totals.setdefault(
            topic_slug,
            {
                "topic": session.test.topic.title,
                "slug": topic_slug,
                "correct": 0,
                "total": 0,
                "attempts": 0,
            },
        )
        topic_data["correct"] += correct
        topic_data["total"] += total
        topic_data["attempts"] += 1

        day = (session.submitted_at or session.created_at).strftime("%a")
        weekly_activity[day] = weekly_activity.get(day, 0) + total

        recent_tests.append(
            {
                "id": session.id,
                "title": session.test.title,
                "slug": session.test.slug,
                "topic": session.test.topic.title,
                "difficulty": session.test.difficulty,
                "score": percent,
                "correct": correct,
                "total": total,
                "submitted_at": (session.submitted_at or session.created_at).isoformat(),
            }
        )

    attempts = len(submitted_sessions)
    average_score = round((correct_total / question_total) * 100) if question_total else 0
    mastery = max(0, min(100, average_score))
    topic_progress = [
        {
            "topic": item["topic"],
            "slug": item["slug"],
            "value": round((item["correct"] / item["total"]) * 100) if item["total"] else 0,
            "attempts": item["attempts"],
        }
        for item in topic_totals.values()
    ]
    topic_progress.sort(key=lambda item: item["value"])

    ordered_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekly = [{"day": day, "value": weekly_activity.get(day, 0)} for day in ordered_days]

    weak_topics = [topic for topic in topic_progress if topic["value"] < 70]
    recommendations = [
        {
            "title": f"{topic['topic']} targeted practice",
            "description": f"{topic['topic']} bo'yicha natija {topic['value']}%. Avval xatolarni ko'rib, keyin qayta test ishlang.",
            "href": f"/subjects/mathematics/topics/{topic['slug']}" if topic["slug"] == "algebra" else "/subjects/mathematics",
        }
        for topic in weak_topics[:3]
    ]
    if not recommendations:
        recommendations = [
            {
                "title": "Algebra retake",
                "description": "Natijani mustahkamlash uchun Algebra bo'limida boshqa darajadagi testni ishlang.",
                "href": "/subjects/mathematics/topics/algebra",
            }
        ]

    return response.Response(
        {
            "name": request.user.get_full_name() or request.user.username if request.user.is_authenticated else "QuestLab Learner",
            "level": "Algebra Builder" if mastery < 80 else "Algebra Master",
            "tests_taken": attempts,
            "average_score": average_score,
            "math_mastery": mastery,
            "answered_questions": question_total,
            "correct_answers": correct_total,
            "topic_progress": topic_progress,
            "weekly_activity": weekly,
            "recent_tests": recent_tests[:6],
            "recommendations": recommendations,
        }
    )

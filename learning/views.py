from django.db.models import Count
from django.utils import timezone
from rest_framework import decorators, response, status, viewsets

from learning.models import (
    Answer,
    ClassStudent,
    ClassTestAssignment,
    ExamPack,
    ExamPackItem,
    Question,
    Skill,
    Subject,
    TeacherClass,
    Test,
    TestSession,
    Topic,
)
from learning.serializers import (
    AnswerSerializer,
    ClassStudentSerializer,
    ClassTestAssignmentSerializer,
    CreateTestSerializer,
    ExamPackItemSerializer,
    ExamPackSerializer,
    QuestionSerializer,
    SkillSerializer,
    SubjectSerializer,
    TeacherClassSerializer,
    TestSerializer,
    TestSessionSerializer,
    TopicSerializer,
)


def request_value(request, key, default=""):
    return request.data.get(key, request.query_params.get(key, default))


def require_manage_code(request, expected):
    if not expected:
        return None
    provided = request_value(request, "manage_code")
    if provided != expected:
        return response.Response({"detail": "Valid manage code is required."}, status=status.HTTP_403_FORBIDDEN)
    return None


def require_manage_key(request, expected):
    if not expected:
        return None
    provided = request_value(request, "manage_key")
    if provided != expected:
        return response.Response({"detail": "Valid manage key is required."}, status=status.HTTP_403_FORBIDDEN)
    return None


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
        status_filter = request.query_params.get("status")
        if not status_filter:
            queryset = queryset.filter(status=Test.PublishStatus.PUBLISHED)
        difficulty = request.query_params.get("difficulty")
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
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
        return CreateTestSerializer if self.action in {"create", "update", "partial_update"} else TestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.save()
        return response.Response(TestSerializer(test).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        denied = require_manage_key(request, instance.manage_key)
        if denied:
            return denied
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        test = serializer.save()
        return response.Response(TestSerializer(test).data)

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = {
            "subject__slug": self.request.query_params.get("subject"),
            "topic__slug": self.request.query_params.get("topic"),
            "difficulty": self.request.query_params.get("difficulty"),
            "status": self.request.query_params.get("status"),
        }
        return queryset.filter(**{key: value for key, value in filters.items() if value})

    def destroy(self, request, *args, **kwargs):
        test = self.get_object()
        denied = require_manage_key(request, test.manage_key)
        if denied:
            return denied
        if test.sessions.exists():
            test.status = Test.PublishStatus.DRAFT
            test.save(update_fields=["status", "updated_at"])
            return response.Response(TestSerializer(test).data)
        return super().destroy(request, *args, **kwargs)

    @decorators.action(detail=True, methods=["post"])
    def start(self, request, slug=None):
        test = self.get_object()
        session = TestSession.objects.create(
            test=test,
            student_name=request.data.get("student_name", "").strip(),
            student_code=request.data.get("student_code", "").strip(),
            user=request.user if request.user.is_authenticated else None,
        )
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


class TeacherClassViewSet(viewsets.ModelViewSet):
    queryset = (
        TeacherClass.objects.prefetch_related("assignments__test", "students")
        .all()
        .order_by("-created_at")
    )
    serializer_class = TeacherClassSerializer
    lookup_field = "slug"

    @decorators.action(detail=True, methods=["post"])
    def join(self, request, slug=None):
        classroom = self.get_object()
        join_code = request.data.get("join_code", "")
        student_name = request.data.get("student_name", "").strip()
        if classroom.visibility == TeacherClass.Visibility.PRIVATE and join_code != classroom.join_code:
            return response.Response({"detail": "Invalid join code."}, status=status.HTTP_403_FORBIDDEN)
        if not student_name:
            return response.Response({"student_name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        student_code = request.data.get("student_code", "").strip()
        if not student_code:
            return response.Response({"student_code": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        student, _ = ClassStudent.objects.get_or_create(
            classroom=classroom,
            student_code=student_code,
            defaults={"name": student_name},
        )
        if student.name != student_name:
            student.name = student_name
            student.save(update_fields=["name", "updated_at"])
        return response.Response(ClassStudentSerializer(student).data)

    @decorators.action(detail=True, methods=["get", "post"])
    def assignments(self, request, slug=None):
        classroom = self.get_object()
        if request.method == "GET":
            assignments = classroom.assignments.select_related("test").order_by("-created_at")
            return response.Response(ClassTestAssignmentSerializer(assignments, many=True).data)

        denied = require_manage_code(request, classroom.manage_code)
        if denied:
            return denied
        serializer = ClassTestAssignmentSerializer(data={**request.data, "classroom": classroom.id})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(classroom=classroom)
        return response.Response(ClassTestAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"], url_path=r"assignments/(?P<assignment_id>[^/.]+)/start")
    def start_assignment(self, request, slug=None, assignment_id=None):
        classroom = self.get_object()
        assignment = ClassTestAssignment.objects.select_related("test").get(id=assignment_id, classroom=classroom)
        if not assignment.is_active:
            return response.Response({"detail": "Assignment is not active."}, status=status.HTTP_400_BAD_REQUEST)
        student_name = request.data.get("student_name", "").strip()
        join_code = request.data.get("join_code", "")
        if classroom.visibility == TeacherClass.Visibility.PRIVATE and join_code != classroom.join_code:
            return response.Response({"detail": "Invalid join code."}, status=status.HTTP_403_FORBIDDEN)
        if not student_name:
            return response.Response({"student_name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        student_code = request.data.get("student_code", "").strip()
        if not student_code:
            return response.Response({"student_code": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        ClassStudent.objects.update_or_create(
            classroom=classroom,
            student_code=student_code,
            defaults={"name": student_name},
        )
        session = TestSession.objects.create(
            test=assignment.test,
            classroom=classroom,
            assignment=assignment,
            student_name=student_name,
            student_code=student_code,
            user=request.user if request.user.is_authenticated else None,
        )
        return response.Response(TestSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["get"])
    def results(self, request, slug=None):
        classroom = self.get_object()
        sessions = (
            TestSession.objects.filter(classroom=classroom, status=TestSession.Status.SUBMITTED)
            .select_related("test", "assignment")
            .prefetch_related("answers", "test__testquestion_set__question__skills")
            .order_by("-submitted_at")
        )
        rows = []
        skill_totals = {}
        score_sum = 0
        for session in sessions:
            questions = [item.question for item in session.test.testquestion_set.all()]
            answer_map = {answer.question_id: answer.value.strip() for answer in session.answers.all()}
            correct = sum(1 for question in questions if answer_map.get(question.id, "") == question.answer.strip())
            total = len(questions)
            score = round((correct / total) * 100) if total else 0
            score_sum += score
            for question in questions:
                is_correct = answer_map.get(question.id, "") == question.answer.strip()
                skills = list(question.skills.all()) or []
                for skill in skills:
                    data = skill_totals.setdefault(skill.title, {"skill": skill.title, "correct": 0, "total": 0})
                    data["correct"] += 1 if is_correct else 0
                    data["total"] += 1
            rows.append(
                {
                    "session_id": session.id,
                    "student_name": session.student_name or "Student",
                    "test_title": session.test.title,
                    "test_slug": session.test.slug,
                    "assignment_id": session.assignment_id,
                    "assignment_title": session.assignment.title if session.assignment else "",
                    "score": score,
                    "correct": correct,
                    "total": total,
                    "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
                }
            )
        weak_skills = [
            {
                **item,
                "percent": round((item["correct"] / item["total"]) * 100) if item["total"] else 0,
            }
            for item in skill_totals.values()
        ]
        weak_skills.sort(key=lambda item: item["percent"])
        count = len(rows)
        return response.Response(
            {
                "classroom": TeacherClassSerializer(classroom).data,
                "attempts": count,
                "average_score": round(score_sum / count) if count else 0,
                "results": rows,
                "weak_skills": weak_skills[:6],
            }
        )


class ExamPackViewSet(viewsets.ModelViewSet):
    queryset = ExamPack.objects.prefetch_related("items__test").all().order_by("-created_at")
    serializer_class = ExamPackSerializer
    lookup_field = "slug"

    @decorators.action(detail=True, methods=["get", "post"])
    def items(self, request, slug=None):
        pack = self.get_object()
        if request.method == "GET":
            return response.Response(ExamPackItemSerializer(pack.items.select_related("test"), many=True).data)

        denied = require_manage_code(request, pack.manage_code)
        if denied:
            return denied
        serializer = ExamPackItemSerializer(data={**request.data, "pack": pack.id})
        serializer.is_valid(raise_exception=True)
        item = serializer.save(pack=pack)
        return response.Response(ExamPackItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"], url_path=r"items/(?P<item_id>[^/.]+)/start")
    def start_item(self, request, slug=None, item_id=None):
        pack = self.get_object()
        item = ExamPackItem.objects.select_related("test").get(id=item_id, pack=pack)
        access_code = request.data.get("access_code", "")
        student_name = request.data.get("student_name", "").strip()
        if not pack.is_active:
            return response.Response({"detail": "Exam pack is not active."}, status=status.HTTP_400_BAD_REQUEST)
        if pack.visibility == ExamPack.Visibility.PRIVATE and access_code != pack.access_code:
            return response.Response({"detail": "Invalid access code."}, status=status.HTTP_403_FORBIDDEN)
        if not student_name:
            return response.Response({"student_name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        student_code = request.data.get("student_code", "").strip()
        if not student_code:
            return response.Response({"student_code": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        session = TestSession.objects.create(
            test=item.test,
            exam_pack=pack,
            exam_pack_item=item,
            student_name=student_name,
            student_code=student_code,
            user=request.user if request.user.is_authenticated else None,
        )
        return response.Response(TestSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["get"])
    def results(self, request, slug=None):
        pack = self.get_object()
        sessions = (
            TestSession.objects.filter(exam_pack=pack, status=TestSession.Status.SUBMITTED)
            .select_related("test", "exam_pack_item")
            .prefetch_related("answers", "test__testquestion_set__question")
            .order_by("-submitted_at")
        )
        rows = []
        score_sum = 0
        for session in sessions:
            questions = [item.question for item in session.test.testquestion_set.all()]
            answer_map = {answer.question_id: answer.value.strip() for answer in session.answers.all()}
            correct = sum(1 for question in questions if answer_map.get(question.id, "") == question.answer.strip())
            total = len(questions)
            score = round((correct / total) * 100) if total else 0
            score_sum += score
            rows.append(
                {
                    "session_id": session.id,
                    "student_name": session.student_name or "Student",
                    "test_title": session.test.title,
                    "test_slug": session.test.slug,
                    "item_id": session.exam_pack_item_id,
                    "item_title": session.exam_pack_item.title if session.exam_pack_item else "",
                    "score": score,
                    "correct": correct,
                    "total": total,
                    "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
                }
            )
        count = len(rows)
        return response.Response(
            {
                "pack": ExamPackSerializer(pack).data,
                "attempts": count,
                "average_score": round(score_sum / count) if count else 0,
                "results": rows,
            }
        )


@decorators.api_view(["GET"])
def profile_summary(request):
    student_code = request.query_params.get("student_code", "").strip()
    sessions = (
        TestSession.objects.select_related("test", "test__topic", "test__subject")
        .prefetch_related("answers", "test__testquestion_set__question")
        .order_by("-created_at")
    )
    if student_code:
        sessions = sessions.filter(student_code=student_code)
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


@decorators.api_view(["GET"])
def mistakes_summary(request):
    student_code = request.query_params.get("student_code", "").strip()
    sessions = (
        TestSession.objects.filter(status=TestSession.Status.SUBMITTED)
        .select_related("test", "test__topic")
        .prefetch_related("answers", "test__testquestion_set__question__skills")
        .order_by("-submitted_at")
    )
    if student_code:
        sessions = sessions.filter(student_code=student_code)
    mistakes = []
    skill_totals = {}
    for session in sessions:
        answer_map = {answer.question_id: answer.value.strip() for answer in session.answers.all()}
        for item in session.test.testquestion_set.all():
            question = item.question
            user_answer = answer_map.get(question.id, "")
            is_correct = user_answer == question.answer.strip()
            skills = list(question.skills.all())
            for skill in skills:
                data = skill_totals.setdefault(skill.title, {"skill": skill.title, "correct": 0, "total": 0})
                data["correct"] += 1 if is_correct else 0
                data["total"] += 1
            if not is_correct:
                mistakes.append(
                    {
                        "session_id": session.id,
                        "question_id": question.id,
                        "test_title": session.test.title,
                        "topic": session.test.topic.title,
                        "prompt": question.prompt,
                        "user_answer": user_answer,
                        "correct_answer": question.answer,
                        "explanation": question.explanation,
                        "skills": [skill.title for skill in skills],
                    }
                )
    weak_skills = [
        {
            **item,
            "percent": round((item["correct"] / item["total"]) * 100) if item["total"] else 0,
        }
        for item in skill_totals.values()
    ]
    weak_skills.sort(key=lambda item: item["percent"])
    return response.Response({"mistakes": mistakes[:50], "weak_skills": weak_skills[:10]})

from rest_framework import serializers

from learning.models import (
    Answer,
    ClassStudent,
    ClassTestAssignment,
    ExamPack,
    ExamPackItem,
    Question,
    RoleProfile,
    Skill,
    Subject,
    TeacherClass,
    Test,
    TestQuestion,
    TestSession,
    Topic,
)


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "title", "slug", "description"]


class RoleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleProfile
        fields = ["identity_code", "display_name", "active_role", "available_roles", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate_active_role(self, value):
        valid_roles = {choice[0] for choice in RoleProfile.Role.choices}
        if value not in valid_roles:
            raise serializers.ValidationError("Invalid role.")
        return value


class TopicSerializer(serializers.ModelSerializer):
    subject_slug = serializers.CharField(source="subject.slug", read_only=True)
    test_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "subject", "subject_slug", "title", "slug", "description", "test_count"]


class SkillSerializer(serializers.ModelSerializer):
    topic_slug = serializers.CharField(source="topic.slug", read_only=True)

    class Meta:
        model = Skill
        fields = ["id", "topic", "topic_slug", "title", "slug", "description"]


class QuestionSerializer(serializers.ModelSerializer):
    skill_titles = serializers.StringRelatedField(source="skills", many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "subject",
            "topic",
            "skills",
            "skill_titles",
            "type",
            "difficulty",
            "prompt",
            "options",
            "answer",
            "explanation",
        ]


class TestQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)

    class Meta:
        model = TestQuestion
        fields = ["order", "question"]


class TestSerializer(serializers.ModelSerializer):
    subject_slug = serializers.CharField(source="subject.slug", read_only=True)
    topic_slug = serializers.CharField(source="topic.slug", read_only=True)
    test_questions = TestQuestionSerializer(source="testquestion_set", many=True, read_only=True)

    class Meta:
        model = Test
        fields = [
            "id",
            "title",
            "slug",
            "subject",
            "subject_slug",
            "topic",
            "topic_slug",
            "difficulty",
            "estimated_minutes",
            "passing_score",
            "status",
            "creator_name",
            "test_questions",
        ]


class CreateTestQuestionSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=Question.QuestionType.choices, default=Question.QuestionType.SINGLE_CHOICE)
    prompt = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    answer = serializers.CharField(allow_blank=True)
    explanation = serializers.CharField(required=False, allow_blank=True)
    skills = serializers.ListField(child=serializers.IntegerField(), required=True, allow_empty=False)


class WriteTestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160)
    slug = serializers.SlugField(max_length=50, required=False)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())
    topic = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.select_related("subject").all())
    difficulty = serializers.ChoiceField(choices=Question.Difficulty.choices)
    estimated_minutes = serializers.IntegerField(min_value=1, default=10)
    passing_score = serializers.IntegerField(min_value=0, max_value=100, default=70)
    status = serializers.ChoiceField(choices=Test.PublishStatus.choices, default=Test.PublishStatus.PUBLISHED)
    creator_name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    creator_code = serializers.CharField(max_length=80, required=False, allow_blank=True, write_only=True)
    manage_key = serializers.CharField(max_length=80, required=False, allow_blank=True, write_only=True)
    questions = CreateTestQuestionSerializer(many=True)

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        subject = attrs.get("subject") or getattr(instance, "subject", None)
        topic = attrs.get("topic") or getattr(instance, "topic", None)
        if topic and subject and topic.subject_id != subject.id:
            raise serializers.ValidationError({"topic": "Topic must belong to selected subject."})
        questions = attrs.get("questions")
        if questions is not None and len(questions) < 1:
            raise serializers.ValidationError({"questions": "At least one question is required."})
        slug = attrs.get("slug")
        if slug and Test.objects.filter(slug=slug).exclude(id=getattr(instance, "id", None)).exists():
            raise serializers.ValidationError({"slug": "A test with this slug already exists."})
        if instance and instance.manage_key:
            manage_key = attrs.get("manage_key") or self.initial_data.get("manage_key")
            if manage_key != instance.manage_key:
                raise serializers.ValidationError({"manage_key": "Valid manage key is required."})
        for index, question in enumerate(questions or [], start=1):
            skill_ids = question.get("skills", [])
            matched_count = Skill.objects.filter(id__in=skill_ids, topic=topic).count()
            if matched_count != len(set(skill_ids)):
                raise serializers.ValidationError({"questions": f"Question {index} has skills outside selected topic."})
        return attrs

    def create(self, validated_data):
        questions_data = validated_data.pop("questions")
        test = Test.objects.create(**validated_data)
        self._replace_questions(test, questions_data)
        return test

    def update(self, instance, validated_data):
        questions_data = validated_data.pop("questions", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if questions_data is not None:
            instance.testquestion_set.all().delete()
            self._replace_questions(instance, questions_data)
        return instance

    def _replace_questions(self, test, questions_data):
        for index, question_data in enumerate(questions_data, start=1):
            skill_ids = question_data.pop("skills", [])
            question = Question.objects.create(
                subject=test.subject,
                topic=test.topic,
                difficulty=test.difficulty,
                **question_data,
            )
            question.skills.set(Skill.objects.filter(id__in=skill_ids, topic=test.topic))
            TestQuestion.objects.create(test=test, question=question, order=index)


CreateTestSerializer = WriteTestSerializer


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ["id", "session", "question", "value", "is_flagged"]


class TestSessionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    test_title = serializers.CharField(source="test.title", read_only=True)
    test_slug = serializers.CharField(source="test.slug", read_only=True)

    class Meta:
        model = TestSession
        fields = [
            "id",
            "test",
            "test_title",
            "test_slug",
            "user",
            "classroom",
            "assignment",
            "exam_pack",
            "exam_pack_item",
            "student_name",
            "student_code",
            "status",
            "submitted_at",
            "answers",
            "created_at",
        ]
        read_only_fields = ["user", "status", "submitted_at", "created_at"]


class ClassStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassStudent
        fields = ["id", "classroom", "name", "student_code", "created_at"]
        read_only_fields = ["classroom", "created_at"]


class ClassTestAssignmentSerializer(serializers.ModelSerializer):
    test_title = serializers.CharField(source="test.title", read_only=True)
    test_slug = serializers.CharField(source="test.slug", read_only=True)
    difficulty = serializers.CharField(source="test.difficulty", read_only=True)
    question_count = serializers.IntegerField(source="test.questions.count", read_only=True)

    class Meta:
        model = ClassTestAssignment
        fields = [
            "id",
            "classroom",
            "test",
            "test_title",
            "test_slug",
            "difficulty",
            "question_count",
            "title",
            "opens_at",
            "closes_at",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["classroom", "created_at"]


class TeacherClassSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(source="students.count", read_only=True)
    assignment_count = serializers.IntegerField(source="assignments.count", read_only=True)
    assignments = ClassTestAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = TeacherClass
        fields = [
            "id",
            "name",
            "slug",
            "teacher_name",
            "visibility",
            "join_code",
            "manage_code",
            "description",
            "student_count",
            "assignment_count",
            "assignments",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class ExamPackItemSerializer(serializers.ModelSerializer):
    test_title = serializers.CharField(source="test.title", read_only=True)
    test_slug = serializers.CharField(source="test.slug", read_only=True)
    difficulty = serializers.CharField(source="test.difficulty", read_only=True)
    question_count = serializers.IntegerField(source="test.questions.count", read_only=True)

    class Meta:
        model = ExamPackItem
        fields = [
            "id",
            "pack",
            "test",
            "test_title",
            "test_slug",
            "difficulty",
            "question_count",
            "title",
            "order",
            "is_required",
            "created_at",
        ]
        read_only_fields = ["pack", "created_at"]


class ExamPackSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source="items.count", read_only=True)
    items = ExamPackItemSerializer(many=True, read_only=True)

    class Meta:
        model = ExamPack
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "exam_type",
            "visibility",
            "access_code",
            "manage_code",
            "price_label",
            "is_active",
            "item_count",
            "items",
            "created_at",
        ]
        read_only_fields = ["created_at"]

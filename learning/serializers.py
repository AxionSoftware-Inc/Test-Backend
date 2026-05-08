from rest_framework import serializers

from learning.models import Answer, Question, Skill, Subject, Test, TestQuestion, TestSession, Topic


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "title", "slug", "description"]


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
            "test_questions",
        ]


class CreateTestQuestionSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=Question.QuestionType.choices, default=Question.QuestionType.SINGLE_CHOICE)
    prompt = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    answer = serializers.CharField(allow_blank=True)
    explanation = serializers.CharField(required=False, allow_blank=True)
    skills = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)


class CreateTestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160)
    slug = serializers.SlugField(max_length=50)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())
    topic = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.select_related("subject").all())
    difficulty = serializers.ChoiceField(choices=Question.Difficulty.choices)
    estimated_minutes = serializers.IntegerField(min_value=1, default=10)
    passing_score = serializers.IntegerField(min_value=0, max_value=100, default=70)
    questions = CreateTestQuestionSerializer(many=True)

    def validate(self, attrs):
        if attrs["topic"].subject_id != attrs["subject"].id:
            raise serializers.ValidationError({"topic": "Topic must belong to selected subject."})
        if len(attrs["questions"]) < 1:
            raise serializers.ValidationError({"questions": "At least one question is required."})
        if Test.objects.filter(slug=attrs["slug"]).exists():
            raise serializers.ValidationError({"slug": "A test with this slug already exists."})
        return attrs

    def create(self, validated_data):
        questions_data = validated_data.pop("questions")
        test = Test.objects.create(**validated_data)
        created_questions = []
        for index, question_data in enumerate(questions_data, start=1):
            skill_ids = question_data.pop("skills", [])
            question = Question.objects.create(
                subject=test.subject,
                topic=test.topic,
                difficulty=test.difficulty,
                **question_data,
            )
            if skill_ids:
                question.skills.set(Skill.objects.filter(id__in=skill_ids, topic=test.topic))
            TestQuestion.objects.create(test=test, question=question, order=index)
            created_questions.append(question)
        return test


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
        fields = ["id", "test", "test_title", "test_slug", "user", "status", "submitted_at", "answers", "created_at"]
        read_only_fields = ["user", "status", "submitted_at", "created_at"]

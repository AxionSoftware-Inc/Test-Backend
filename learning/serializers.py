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

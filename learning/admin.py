from django.contrib import admin

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
    TestQuestion,
    TestSession,
    Topic,
)


class TestQuestionInline(admin.TabularInline):
    model = TestQuestion
    extra = 0


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "topic", "difficulty", "estimated_minutes"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TestQuestionInline]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "slug"]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ["title", "topic", "slug"]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["id", "topic", "difficulty", "type"]
    list_filter = ["topic", "difficulty", "type"]
    filter_horizontal = ["skills"]


admin.site.register(TestSession)
admin.site.register(Answer)
admin.site.register(TeacherClass)
admin.site.register(ClassStudent)
admin.site.register(ClassTestAssignment)
admin.site.register(ExamPack)
admin.site.register(ExamPackItem)

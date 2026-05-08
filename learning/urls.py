from rest_framework.routers import DefaultRouter

from django.urls import path

from learning.views import (
    QuestionViewSet,
    SkillViewSet,
    SubjectViewSet,
    TestSessionViewSet,
    TestViewSet,
    TopicViewSet,
    profile_summary,
)

router = DefaultRouter()
router.register("subjects", SubjectViewSet)
router.register("topics", TopicViewSet)
router.register("skills", SkillViewSet)
router.register("questions", QuestionViewSet)
router.register("tests", TestViewSet)
router.register("sessions", TestSessionViewSet)

urlpatterns = [
    path("profile/summary/", profile_summary),
    *router.urls,
]

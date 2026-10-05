from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ObjectiveViewSet, PlayerProfileView, ProgressView, QuestViewSet, TraderViewSet


router = DefaultRouter()
router.register("traders", TraderViewSet, basename="trader")
router.register("quests", QuestViewSet, basename="quest")
router.register("objectives", ObjectiveViewSet, basename="objective")

urlpatterns = [
    path("", include(router.urls)),
    path("player/", PlayerProfileView.as_view(), name="player-profile"),
    path("progress/", ProgressView.as_view(), name="progress"),
]

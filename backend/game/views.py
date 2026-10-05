from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PlayerProfile, Quest, QuestObjective, Submission, Trader
from .serializers import (
    PlayerProfileSerializer,
    QuestDetailSerializer,
    QuestListSerializer,
    SubmissionCreateSerializer,
    SubmissionSerializer,
    TraderSerializer,
)
from .services import complete_quest, start_quest


class TraderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TraderSerializer

    def get_queryset(self):
        return Trader.objects.filter(available=True).order_by("sort_order", "id")

    @action(detail=True, methods=["get"])
    def quests(self, request, pk=None):
        trader = self.get_object()
        quests = trader.quests.prefetch_related("objectives__submissions", "objectives__item", "objectives__location", "requirements__required_quest").order_by("sort_order", "id")
        serializer = QuestDetailSerializer(quests, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class QuestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    def get_queryset(self):
        queryset = Quest.objects.select_related("trader").prefetch_related(
            "objectives__item",
            "objectives__location",
            "objectives__submissions",
            "requirements__required_quest",
        )

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        trader_slug = self.request.query_params.get("trader")
        if trader_slug:
            queryset = queryset.filter(trader__slug=trader_slug)

        return queryset.order_by("sort_order", "id")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return QuestDetailSerializer
        return QuestListSerializer

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        quest = self.get_object()
        quest = start_quest(quest)
        serializer = QuestDetailSerializer(quest, context=self.get_serializer_context())
        return Response(serializer.data)


    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        quest = complete_quest(self.get_object())
        return Response(QuestDetailSerializer(quest, context=self.get_serializer_context()).data)


class ObjectiveViewSet(viewsets.GenericViewSet):
    queryset = QuestObjective.objects.select_related("quest")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        objective = self.get_object()
        serializer = SubmissionCreateSerializer(data=request.data, context={"objective": objective})
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        response_serializer = SubmissionSerializer(submission)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PlayerProfileView(APIView):
    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(pk=1)
        return Response(PlayerProfileSerializer(profile, context={"request": request}).data)


class ProgressView(APIView):
    def get(self, request):
        quest_counts = Quest.objects.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=Quest.Status.COMPLETED)),
            active=Count("id", filter=Q(status=Quest.Status.ACTIVE)),
            available=Count("id", filter=Q(status=Quest.Status.AVAILABLE)),
            locked=Count("id", filter=Q(status=Quest.Status.LOCKED)),
        )
        objective_counts = QuestObjective.objects.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(completed=True)),
        )

        return Response(
            {
                "quests": quest_counts,
                "objectives": objective_counts,
            }
        )

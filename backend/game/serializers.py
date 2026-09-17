from rest_framework import serializers

from .models import Item, Location, Quest, QuestObjective, Submission, Trader


class TraderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trader
        fields = ["id", "slug", "name", "description", "image", "available"]


class TraderShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trader
        fields = ["id", "slug", "name"]


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "slug", "name", "description", "image"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "slug", "name", "description", "image"]


class QuestObjectiveSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    latest_submission = serializers.SerializerMethodField()

    def get_latest_submission(self, objective):
        submission = next(iter(objective.submissions.all()), None)
        return SubmissionSerializer(submission).data if submission else None

    class Meta:
        model = QuestObjective
        fields = [
            "id",
            "type",
            "title",
            "description",
            "required_amount",
            "current_amount",
            "completed",
            "completed_at",
            "sort_order",
            "metadata",
            "item",
            "location",
            "latest_submission",
        ]


class QuestListSerializer(serializers.ModelSerializer):
    trader = TraderShortSerializer(read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Quest
        fields = ["id", "slug", "title", "description", "status", "trader", "progress", "sort_order"]

    def get_progress(self, quest: Quest) -> dict[str, int]:
        objectives = quest.objectives.all()
        return {
            "completed": sum(1 for objective in objectives if objective.completed),
            "total": len(objectives),
        }


class RequirementSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="required_quest.id")
    slug = serializers.SlugField(source="required_quest.slug")
    title = serializers.CharField(source="required_quest.title")
    status = serializers.CharField(source="required_quest.status")


class QuestDetailSerializer(QuestListSerializer):
    objectives = QuestObjectiveSerializer(many=True, read_only=True)
    requirements = RequirementSerializer(many=True, read_only=True)

    class Meta(QuestListSerializer.Meta):
        fields = QuestListSerializer.Meta.fields + ["objectives", "requirements"]


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ["id", "objective", "amount", "status", "comment", "proof", "created_at", "admin_comment", "reviewed_at"]
        read_only_fields = ["id", "objective", "status", "created_at"]


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ["amount", "comment", "proof"]

    def validate_amount(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError("Amount must be greater than or equal to 1.")
        return value

    def validate(self, attrs: dict) -> dict:
        objective: QuestObjective = self.context["objective"]

        if objective.completed:
            raise serializers.ValidationError({"detail": "Cannot submit a completed objective."})

        if objective.quest.status != Quest.Status.ACTIVE:
            raise serializers.ValidationError({"detail": "Submissions are allowed only for active quests."})

        if attrs.get("amount", 1) > objective.required_amount - objective.current_amount:
            raise serializers.ValidationError({"amount": "Amount exceeds remaining objective progress."})

        pending_exists = Submission.objects.filter(
            objective=objective,
            status=Submission.Status.PENDING,
        ).exists()
        if pending_exists:
            raise serializers.ValidationError({"detail": "A pending submission already exists for this objective."})

        return attrs

    def create(self, validated_data: dict) -> Submission:
        return Submission.objects.create(
            objective=self.context["objective"],
            status=Submission.Status.PENDING,
            **validated_data,
        )

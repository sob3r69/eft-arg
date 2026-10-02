from django.contrib import admin, messages
from django.db.models import Case, IntegerField, When

from .models import Item, Location, Quest, QuestObjective, QuestRequirement, Submission, Trader
from .services import approve_submission, reject_submission


@admin.register(Trader)
class TraderAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "available", "sort_order"]
    list_filter = ["available"]
    search_fields = ["name", "description"]
    ordering = ["sort_order", "id"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ["name"]}


class QuestRequirementInline(admin.TabularInline):
    model = QuestRequirement
    fk_name = "quest"
    extra = 1


class QuestObjectiveInline(admin.TabularInline):
    model = QuestObjective
    extra = 1
    fields = [
        "type",
        "title",
        "description",
        "required_amount",
        "current_amount",
        "completed",
        "sort_order",
        "item",
        "location",
        "metadata",
    ]


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ["title", "trader", "status", "sort_order"]
    list_filter = ["trader", "status"]
    search_fields = ["title", "description"]
    ordering = ["sort_order", "id"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [QuestRequirementInline, QuestObjectiveInline]


@admin.register(QuestObjective)
class QuestObjectiveAdmin(admin.ModelAdmin):
    list_display = ["title", "quest", "type", "current_amount", "required_amount", "completed", "sort_order"]
    list_filter = ["type", "completed", "quest"]
    search_fields = ["title", "description"]
    ordering = ["quest", "sort_order", "id"]


@admin.action(description="Approve selected submissions")
def approve_selected_submissions(modeladmin, request, queryset):
    approved = 0
    for submission in queryset:
        previous_status = submission.status
        updated_submission = approve_submission(submission)
        if previous_status == Submission.Status.PENDING and updated_submission.status == Submission.Status.APPROVED:
            approved += 1

    modeladmin.message_user(request, f"Approved submissions: {approved}", messages.SUCCESS)


@admin.action(description="Reject selected submissions")
def reject_selected_submissions(modeladmin, request, queryset):
    rejected = 0
    for submission in queryset:
        previous_status = submission.status
        updated_submission = reject_submission(submission)
        if previous_status == Submission.Status.PENDING and updated_submission.status == Submission.Status.REJECTED:
            rejected += 1

    modeladmin.message_user(request, f"Rejected submissions: {rejected}", messages.SUCCESS)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ["id", "objective", "quest", "status", "amount", "created_at", "reviewed_at"]
    list_filter = ["status", "objective__quest"]
    search_fields = ["objective__title", "comment", "proof", "admin_comment"]
    readonly_fields = [
        "objective", "amount", "status", "comment", "proof", "created_at", "reviewed_at",
        "telegram_message_id", "telegram_status",
    ]
    change_form_template = "admin/game/submission/change_form.html"
    ordering = ["-created_at", "-id"]
    actions = [approve_selected_submissions, reject_selected_submissions]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        if "_approve" in request.POST:
            approve_submission(obj)
            self.message_user(request, "Заявка подтверждена. Прогресс обновлён.", messages.SUCCESS)
        elif "_reject" in request.POST:
            reject_submission(obj, obj.admin_comment)
            self.message_user(request, "Заявка отклонена.", messages.SUCCESS)
        return super().response_change(request, obj)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("objective__quest")
            .annotate(
                pending_first=Case(
                    When(status=Submission.Status.PENDING, then=0),
                    default=1,
                    output_field=IntegerField(),
                )
            )
            .order_by("pending_first", "-created_at", "-id")
        )

    @admin.display(description="Quest")
    def quest(self, submission: Submission):
        return submission.objective.quest

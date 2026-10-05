from django.core.validators import MinValueValidator
from django.db import models


class PlayerProfile(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    nickname = models.CharField("Никнейм", max_length=100, default="Игрок")
    avatar = models.ImageField("Аватар", upload_to="players/", max_length=255, blank=True)
    rubles = models.PositiveBigIntegerField("Рубли", default=0)
    euros = models.PositiveBigIntegerField("Евро", default=0)
    dollars = models.PositiveBigIntegerField("Доллары", default=0)
    experience = models.PositiveBigIntegerField("Опыт", default=0)
    experience_per_level = models.PositiveIntegerField(
        "Опыт на уровень", default=10000, validators=[MinValueValidator(1)],
        help_text="Уровень = 1 + целая часть (опыт / опыт на уровень).",
    )

    class Meta:
        verbose_name = "Профиль игрока"
        verbose_name_plural = "Профиль игрока"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="single_player_profile")]

    @property
    def level(self):
        return 1 + self.experience // self.experience_per_level

    def __str__(self):
        return self.nickname


class Trader(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="traders/", max_length=255, blank=True)
    reputation = models.DecimalField("Текущая репутация", max_digits=12, decimal_places=2, default=0)
    available = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class Quest(models.Model):
    class Status(models.TextChoices):
        LOCKED = "locked", "Locked"
        AVAILABLE = "available", "Available"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    trader = models.ForeignKey(Trader, on_delete=models.CASCADE, related_name="quests")
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="quests/", max_length=255, blank=True)
    reputation_reward = models.DecimalField("Награда: репутация", max_digits=8, decimal_places=2, default=0)
    rubles_reward = models.PositiveBigIntegerField("Награда: рубли", default=0)
    euros_reward = models.PositiveBigIntegerField("Награда: евро", default=0)
    dollars_reward = models.PositiveBigIntegerField("Награда: доллары", default=0)
    experience_reward = models.PositiveBigIntegerField("Награда: опыт", default=0)
    rewards_granted_at = models.DateTimeField(null=True, blank=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LOCKED)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class QuestRequirement(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name="requirements")
    required_quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name="required_for")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["quest", "required_quest"], name="unique_quest_requirement"),
            models.CheckConstraint(
                condition=~models.Q(quest=models.F("required_quest")),
                name="quest_cannot_require_itself",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quest} requires {self.required_quest}"


class QuestObjective(models.Model):
    class Type(models.TextChoices):
        FIND_ITEM = "find_item", "Find item"
        HANDOVER_ITEM = "handover_item", "Hand over item"
        VISIT_LOCATION = "visit_location", "Visit location"
        ENTER_CODE = "enter_code", "Enter code"
        SCAN_QR = "scan_qr", "Scan QR"
        CUSTOM = "custom", "Custom"

    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name="objectives")
    type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    required_amount = models.PositiveIntegerField(default=1)
    current_amount = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    item = models.ForeignKey(
        Item,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="objectives",
    )
    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="objectives",
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    objective = models.ForeignKey(QuestObjective, on_delete=models.CASCADE, related_name="submissions")
    amount = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    comment = models.TextField(blank=True)
    proof = models.CharField(max_length=500, blank=True)
    admin_comment = models.TextField(blank=True)
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    telegram_status = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Submission #{self.pk} for {self.objective}"

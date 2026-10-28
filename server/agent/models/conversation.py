from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Max, Q
from suvereo_common.structures import LLMFile

from account.authorization import PERMISSIONS, datasets_with_permission
from agent.models.agent import Agent
from catalog.models import DataSet


def conversation_file_path(instance, filename):
    return f"conversations/{instance.conversation.id}/{filename}"


class ConversationQuerySet(models.QuerySet):
    def visible_to(self, user) -> "ConversationQuerySet":
        """Conversations `user` owns or may view through `CONVERSATION.VIEW_ALL` on their data set."""
        return self.filter(
            Q(user=user) | Q(data_set__in=datasets_with_permission(user, PERMISSIONS.CONVERSATION.VIEW_ALL))
        )

    def last_activity(self):
        """When the latest of these conversations started or got a message, or None for no conversations."""
        latest = self.aggregate(started=Max("started_at"), messaged=Max("messages__created_at"))
        return max((t for t in latest.values() if t is not None), default=None)


class ConversationManager(models.Manager.from_queryset(ConversationQuerySet)):
    """Hides temporary conversations, such as evaluation runs; use Conversation.all_objects to include them."""

    def get_queryset(self):
        return super().get_queryset().filter(is_temporary=False)


class Conversation(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    started_at = models.DateTimeField(auto_now_add=True)
    data_set = models.ForeignKey(DataSet, on_delete=models.PROTECT, null=False)
    summary = models.CharField(null=True)
    conversation_summary = models.TextField(null=True, blank=True)
    last_summarized_message = models.ForeignKey(
        "agent.Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=False)
    is_temporary = models.BooleanField(
        default=False, db_comment="Created for a short-lived purpose, e.g. an evaluation run; hidden and deleted after."
    )

    objects = ConversationManager()
    all_objects = ConversationQuerySet.as_manager()

    class Meta:
        db_table_comment = (
            "A conversation is a collection of various messages exchanged during one session. Messages "
            "are mostly questions and answers and have different actors such as end user asking "
            "question and ECL agent answering those questions."
        )
        permissions = [("converse", "Can converse with agents")]


class ConversationFile(models.Model):
    class FileCategory(models.TextChoices):
        IMAGE = "image", "Image"
        FILE = "file", "File"

    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name="files")
    file = models.FileField(upload_to=conversation_file_path)
    file_category = models.CharField(choices=FileCategory.choices, max_length=32)
    content_type = models.CharField(max_length=255, null=True)
    llm_content = models.TextField(blank=True)

    is_hidden = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file.name

    def get_llm_file_object(self):
        return LLMFile(
            id=self.pk,
            content=self.llm_content,
            filename=self.file.name.split("/")[-1].split(".")[0],
            content_type=self.content_type,
            file_category=self.file_category,
        )

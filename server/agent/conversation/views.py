import os

from django.conf import settings
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import (
    PERMISSIONS,
    datasets_with_permission,
    enforce_dataset_scoped_permission,
    has_dataset_perm,
)
from agent.conversation.manager import ConversationManager
from agent.conversation.models import Conversation, ConversationFile, Message
from agent.conversation.serializers import (
    AskQuestionSerializer,
    ConversationContentSerializer,
    ConversationCreationSerializer,
    ConversationSerializer,
    FileUploadTaskResponseSerializer,
    MessageFeedbackSerializer,
    SupportedFileTypesSerializer,
)
from agent.conversation.services import ConversationFileMessageService
from agent.conversation.tasks import process_file_upload_task, respond_to_user_message_task
from agent.core.registries.agents.agent_registry import AgentRegistry, AgentRegistryError
from agent.core.registries.language_models import LanguageModelRegistry
from agent.core.repositories import DjangoDataSetRepository
from agent.models.agent import Agent
from catalog.models import DataSet


class ConversationView(APIView):
    permission_classes = [IsAuthenticated]
    """
    View to retrieve details of an existing conversation.
    """

    @swagger_auto_schema(
        operation_description="Retrieve details of a conversation",
        manual_parameters=[
            openapi.Parameter(
                "conversation_id", openapi.IN_PATH, description="ID of the conversation", type=openapi.TYPE_INTEGER
            )
        ],
        responses={200: ConversationContentSerializer()},
    )
    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation.objects.select_related("agent")
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=Message.objects.exclude(type__in=Message.internal_message_types()).order_by("id"),
                )
            )
            .filter(
                Q(user=request.user)
                | Q(data_set__in=datasets_with_permission(request.user, PERMISSIONS.CONVERSATION.VIEW_ALL))
            ),
            id=conversation_id,
        )
        serializer = ConversationContentSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Ask a question in a conversation",
        request_body=AskQuestionSerializer,
    )
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        serializer = AskQuestionSerializer(data=request.data, context={"conversation_id": conversation_id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if not has_dataset_perm(request.user, PERMISSIONS.CONVERSATION.CONVERSE, conversation.data_set):
            # 403 rather than the 404-obscuring enforce_dataset_scoped_permission: the owner-scoped
            # fetch above already means this caller legitimately knows the dataset exists.
            self.permission_denied(request)
        if conversation.agent.deleted_at is not None or hasattr(conversation, "agentic_execution"):
            return Response({"detail": "Conversation locked."}, status=status.HTTP_400_BAD_REQUEST)

        if file_ids := serializer.validated_data.get("file_ids"):
            files = ConversationFile.objects.filter(conversation_id=conversation_id, pk__in=file_ids, is_hidden=True)
            for file in files:
                ConversationFileMessageService.create_for_file(file)
                file.is_hidden = False
                file.save()

        data_set_id = serializer.validated_data.get("data_set_id")
        question_message = serializer.validated_data.get("question_message")
        data_set = Conversation.objects.get(id=conversation_id).data_set
        data_set_repo = DjangoDataSetRepository(DataSet)
        language_model_provider_class = LanguageModelRegistry(data_set_repo).provider_for_dataset(data_set.id)
        streaming = language_model_provider_class.STREAMING_AVAILABLE and serializer.validated_data.get("streaming")
        task = respond_to_user_message_task.apply_async(
            kwargs={
                "conversation_id": conversation_id,
                "data_set_id": data_set_id,
                "user_id": request.user.id,
                "message": question_message,
                "streaming": streaming,
            }
        )

        return Response(
            {"task_id": task.id, "streaming": streaming},
            status=status.HTTP_202_ACCEPTED,
        )


class ConversationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    @swagger_auto_schema(
        operation_description="List conversations for a user",
        manual_parameters=[
            openapi.Parameter(
                "data_set_id", openapi.IN_QUERY, description="ID of the data set", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter("agent_id", openapi.IN_QUERY, description="ID of the agent", type=openapi.TYPE_INTEGER),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        data_set_id = self.request.query_params.get("data_set_id")
        agent_id = self.request.query_params.get("agent_id")

        qs = Conversation.objects.filter(
            Q(user=user) | Q(data_set__in=datasets_with_permission(user, PERMISSIONS.CONVERSATION.VIEW_ALL))
        ).exclude(agentic_execution__isnull=False)

        if data_set_id:
            qs = qs.filter(data_set_id=data_set_id)
        if agent_id:
            qs = qs.filter(agent_id=agent_id)

        return qs.order_by("-started_at")

    @swagger_auto_schema(
        operation_description="Create a new conversation",
        request_body=ConversationCreationSerializer,
        responses={201: ConversationContentSerializer()},
    )
    def post(self, request):
        input_serializer = ConversationCreationSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        agent = get_object_or_404(Agent, id=input_serializer.validated_data.get("agent_id"))
        enforce_dataset_scoped_permission(self, PERMISSIONS.CONVERSATION.CONVERSE, agent.dataset, obscured_model=Agent)

        conversation = ConversationManager().create_conversation(user_id=request.user.id, agent_id=agent.id)
        conversation = Conversation.objects.select_related("agent").prefetch_related("messages").get(pk=conversation.pk)
        serializer = ConversationContentSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageFeedbackView(APIView):
    permission_classes = [IsAuthenticated]
    """View to provide feedback on a message."""

    @swagger_auto_schema(
        operation_description="Provide feedback on a message",
        request_body=MessageFeedbackSerializer,
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_PATH, description="ID of the message", type=openapi.TYPE_INTEGER)
        ],
    )
    def patch(self, request, id):
        message = get_object_or_404(Message, id=id, conversation__user=request.user)

        serializer = MessageFeedbackSerializer(message, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConversationFileUploadView(APIView):
    parser_classes = (MultiPartParser,)
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Upload a single file to conversation asynchronously.",
        manual_parameters=[
            openapi.Parameter(
                "file", openapi.IN_FORM, description="File to upload", type=openapi.TYPE_FILE, required=True
            )
        ],
        responses={202: FileUploadTaskResponseSerializer()},
    )
    def post(self, request, conversation_id, *args, **kwargs):
        conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)

        if not has_dataset_perm(request.user, PERMISSIONS.CONVERSATION.CONVERSE, conversation.data_set):
            # 403, not 404 - same reasoning as ConversationView.post.
            self.permission_denied(request)

        try:
            agent_class = AgentRegistry().get_agent_class_by_type(conversation.agent.agent_type)
        except AgentRegistryError:
            return Response(
                {"detail": "This conversation's agent type is unavailable, so file upload is not supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not agent_class.FILE_UPLOAD:
            return Response(
                {"detail": "This conversation's agent does not accept file uploads."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "file" not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        file_extension = os.path.splitext(file.name)[1].lower()
        supported_extensions = []
        for extensions_tuple in settings.FILE_PARSER_CLASSES.keys():
            supported_extensions.extend(extensions_tuple)

        if file_extension not in supported_extensions:
            return Response(
                {
                    "error": f"File type {file_extension} is not supported. Supported types: {', '.join(supported_extensions)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_content = file.read()
        filename = file.name
        content_type = getattr(file, "content_type", "")

        task = process_file_upload_task.apply_async(
            kwargs={
                "conversation_id": conversation_id,
                "file_content": file_content,
                "filename": filename,
                "content_type": content_type,
            }
        )

        response_data = {"task_id": task.id}
        response_serializer = FileUploadTaskResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return Response(
            response_serializer.validated_data,
            status=status.HTTP_202_ACCEPTED,
        )


class SupportedFileTypesView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get list of supported file types for upload",
        responses={200: SupportedFileTypesSerializer()},
    )
    def get(self, request):
        supported_extensions = []
        for extensions_tuple in settings.FILE_PARSER_CLASSES.keys():
            supported_extensions.extend(extensions_tuple)

        response_data = {"supported_extensions": supported_extensions}

        serializer = SupportedFileTypesSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

# Run a Conversation via the API

A [conversation](/docs/concepts#conversation) is an exchange between a user and an agent. Through the API, a conversation is created with an agent, messages are sent to it, and the agent's answers are read from the conversation history. Answers are produced in the background, so a message is sent first and its status is polled afterwards.

All requests carry the `Authorization` header, see [Connecting to the API](/docs/integrate/connect-to-api). The examples use a hypothetical support assistant agent. The agents on your instance, and their answers, differ.

## Find an Agent

A conversation is held with one agent. List the agents of a data set to find its id:

```http
GET /api/agents?dataset=1
Authorization: Token <API_TOKEN>
```

## Create a Conversation

```http
POST /api/conversations
Content-Type: application/json
Authorization: Token <API_TOKEN>

{
  "agent_id": 7
}
```

**Response (`201 Created`):**
```json
{
  "id": 1,
  "started_at": "2025-03-20T10:00:00Z",
  "summary": null,
  "history": [],
  "agent": { "id": 7, "name": "Support Assistant", ... },
  "is_execution_conversation": false,
  "user_email": "service-account@example.com"
}
```

The conversation belongs to the account that created it, and the data set is the agent's.

## Send a Message

```http
POST /api/conversations/{conversation_id}
Content-Type: application/json
Authorization: Token <API_TOKEN>

{
  "question_message": "Does the Business Duplex plan include an SLA?"
}
```

**Response (`202 Accepted`):**
```json
{
  "task_id": "dbe41a42-f678-40c7-8b4c-437fa1673d7d",
  "streaming": false
}
```

The message is processed asynchronously, and `task_id` identifies the processing. The conversation of an agent that has been deleted, and the conversation of an agentic execution, reject new messages with 400.

## Check the Processing Status

```http
GET /api/message-push-status/{task_id}/
Authorization: Token <API_TOKEN>
```

**Response:**
```json
{
  "task_id": "dbe41a42-f678-40c7-8b4c-437fa1673d7d",
  "status": "SUCCESS",
  "result": {
    "conversation_id": 1,
    "message_id": 2
  }
}
```

`status` is one of:
- `PENDING`: the message is still being processed
- `SUCCESS`: the message has been processed
- `FAILURE`: the processing failed, and `result.error` describes why

Poll this endpoint periodically, for example every 2 seconds, until the status is `SUCCESS` or `FAILURE`. Then fetch the conversation to read the answer.

## Get Messages

```http
GET /api/conversations/{conversation_id}
Authorization: Token <API_TOKEN>
```

**Response:**
```json
{
  "id": 1,
  "started_at": "2025-03-20T10:00:00Z",
  "summary": null,
  "history": [
    {
      "id": 1,
      "text": "Does the Business Duplex plan include an SLA?",
      "type": "human",
      "file_type": null,
      "file_name": null
    },
    {
      "id": 2,
      "text": "Yes, the plan includes an SLA with an optional priority support package.",
      "type": "ai",
      "file_type": null,
      "file_name": null
    }
  ],
  "agent": { "id": 7, "name": "Support Assistant", ... },
  "is_execution_conversation": false,
  "user_email": "service-account@example.com"
}
```

Each message in `history` has:
- `id`: the message identifier
- `text`: the message content
- `type`: `human` for the messages you sent, `ai` for the agent's answers, and `file` for an attached file (with `file_type` and `file_name` set)

`GET /api/conversations` lists conversations, and accepts `data_set_id` and `agent_id` as query parameters.

## Send Files

If the agent accepts file uploads, a file is uploaded to the conversation first and then attached to a message.

1. Upload the file with `multipart/form-data`. The response contains a `task_id`:

   ```http
   POST /api/conversations/{conversation_id}/upload/
   Content-Type: multipart/form-data
   Authorization: Token <API_TOKEN>

   file=@report.pdf
   ```

2. Poll `GET /api/file-upload-status/{task_id}/` the same way as the message status, until `status` is `SUCCESS`. The result contains the `file_id` of the uploaded file.

3. Send a message with the file attached:

   ```http
   POST /api/conversations/{conversation_id}
   Content-Type: application/json
   Authorization: Token <API_TOKEN>

   {
     "question_message": "Summarize this report.",
     "file_ids": [4]
   }
   ```

`GET /api/supported-file-types/` returns the supported file extensions. Uploading a file to an agent that does not accept files, or a file of an unsupported type, returns 400.

## Authentication and Authorization

All endpoints require authentication, see [Connecting to the API](/docs/integrate/connect-to-api).

Access to conversations depends on the permissions of the account, which are set through roles, see [Roles and Groups](/docs/management/roles-and-groups#permissions).

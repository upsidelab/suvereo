# Run an Agentic Execution via the API

An [agentic execution](/docs/concepts#agentic-execution) is an autonomous run of an agent, submitted through the API and polled for its result. Unlike a conversation, it has no back-and-forth: you submit input, wait for the run to finish, and retrieve structured output. The execution types of an agent are defined in code, see [Agentic Execution](/docs/agents/agentic-execution).

The examples on this page use a hypothetical "Summarize Document" execution. The execution types available on your instance, and their input and result, are defined by its agents.

## List Available Execution Types

Before starting an execution, retrieve the execution types registered for the chosen agent. The response includes the input schema for each type, which you use to construct a valid request body.

```http
GET /api/agents/{agent_id}/agentic-execution-definitions/
Authorization: Token <API_TOKEN>
```

**Response:**
```json
[
  {
    "key": "summarize-document",
    "name": "Summarize Document",
    "description": null,
    "input_schema": {
      "title": "SummarizeDocumentInput",
      "description": "Input for the document summary execution.",
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "additional_instructions": {
          "title": "Additional Instructions",
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        },
        "topics": {
          "title": "Topics",
          "anyOf": [{ "items": { "type": "string" }, "type": "array" }, { "type": "null" }],
          "default": null
        }
      }
    }
  }
]
```

Returns an empty list if no execution types are registered for the agent. Returns 404 if the agent does not exist.

## Start an Execution

```http
POST /api/agents/{agent_id}/agentic-executions/
Content-Type: application/json
Authorization: Token <API_TOKEN>

{
  "execution_key": "summarize-document",
  "input": {
    "additional_instructions": "Keep each summary under 100 words.",
    "topics": ["pricing", "support"]
  }
}
```

**Response (`202 Accepted`):**
```json
{
  "id": 42,
  "agent": 7,
  "execution_key": "summarize-document",
  "conversation": 198,
  "status": "pending",
  "input": {
    "additional_instructions": "Keep each summary under 100 words.",
    "topics": ["pricing", "support"]
  },
  "result": null,
  "failure_code": null,
  "failure_explanation": null,
  "celery_task_id": "debf5bf6-3e58-4c7d-9e30-c5a4055d951f",
  "started_at": "2025-04-10T14:00:00.000000Z",
  "finished_at": null,
  "duration_seconds": null,
  "user_email": "service-account@example.com",
  "files": [
    {
      "id": 4,
      "filename": "handbook.pdf",
      "file_url": "/media/conversations/198/handbook.pdf",
      "content_type": "application/pdf"
    }
  ]
}
```

Returns 400 if `execution_key` is unknown or belongs to a different agent type, or if `input` fails validation against the execution type's schema. Returns 404 if the agent does not exist.

### Sending Files

If the selected agent has file upload enabled, you can attach files using `multipart/form-data`. The `input` field must be a JSON-encoded string in this case.

```http
POST /api/agents/{agent_id}/agentic-executions/
Content-Type: multipart/form-data
Authorization: Token <API_TOKEN>

input={"additional_instructions": "Keep each summary under 100 words."}
files[]=@handbook.pdf
```

Sending files to an agent with file upload disabled returns 400. Unsupported file types are also rejected with 400.

## Get Execution

```http
GET /api/agentic-executions/{execution_id}/
Authorization: Token <API_TOKEN>
```

**Response (in progress):**
```json
{
  "id": 42,
  "agent": 7,
  "execution_key": "summarize-document",
  "conversation": 198,
  "status": "in_progress",
  "input": { "topics": ["pricing", "support"], "additional_instructions": null },
  "result": null,
  "failure_code": null,
  "failure_explanation": null,
  "celery_task_id": "debf5bf6-3e58-4c7d-9e30-c5a4055d951f",
  "started_at": "2025-04-10T14:00:00.000000Z",
  "finished_at": null,
  "duration_seconds": null,
  "user_email": "service-account@example.com",
  "files": [
    {
      "id": 4,
      "filename": "handbook.pdf",
      "file_url": "/media/conversations/198/handbook.pdf",
      "content_type": "application/pdf"
    }
  ]
}
```

**Response (finished):**
```json
{
  "id": 42,
  "agent": 7,
  "execution_key": "summarize-document",
  "conversation": 198,
  "status": "finished",
  "input": { "topics": ["pricing", "support"], "additional_instructions": null },
  "result": {
    "pricing": "Plans are billed monthly or yearly, ...",
    "support": "Support is available on weekdays, ..."
  },
  "failure_code": null,
  "failure_explanation": null,
  "celery_task_id": "debf5bf6-3e58-4c7d-9e30-c5a4055d951f",
  "started_at": "2025-04-10T14:00:00.000000Z",
  "finished_at": "2025-04-10T14:00:16.000000Z",
  "duration_seconds": 16.554571,
  "user_email": "service-account@example.com",
  "files": [
    {
      "id": 4,
      "filename": "handbook.pdf",
      "file_url": "/media/conversations/198/handbook.pdf",
      "content_type": "application/pdf"
    }
  ]
}
```

**Response (failed):**
```json
{
  "id": 42,
  "agent": 7,
  "execution_key": "summarize-document",
  "conversation": 198,
  "status": "failed",
  "input": { "topics": ["pricing", "support"], "additional_instructions": null },
  "result": null,
  "failure_code": "validation_failed",
  "failure_explanation": "The summary of the topic \"support\" exceeds the length limit.",
  "celery_task_id": "debf5bf6-3e58-4c7d-9e30-c5a4055d951f",
  "started_at": "2025-04-10T14:00:00.000000Z",
  "finished_at": "2025-04-10T14:00:18.000000Z",
  "duration_seconds": 18.230887,
  "user_email": "service-account@example.com",
  "files": [
    {
      "id": 4,
      "filename": "handbook.pdf",
      "file_url": "/media/conversations/198/handbook.pdf",
      "content_type": "application/pdf"
    }
  ]
}
```

### Failure codes

| Code | Meaning |
|------|---------|
| `runtime_error` | An unexpected error occurred during execution |
| `max_retries_exceeded` | The LLM failed to pass validators after the maximum number of correction cycles |
| `validation_failed` | A validator rejected the response without allowing a retry |
| `unknown` | Execution reported failure but returned no structured failure code |

Individual execution definitions may register additional domain-specific failure codes.

## List Executions

```http
GET /api/agentic-executions/
Authorization: Token <API_TOKEN>
```

Supports `agent_id`, `status` (`pending`, `in_progress`, `finished`, `failed`), and `dataset_id` as query parameters. Results are paginated (25 per page) and ordered newest first.

## Authentication and Authorization

All endpoints require authentication, see [Connecting to the API](/docs/connect/connect-to-api).

Access to agentic executions depends on the permissions of the account, which are set through roles, see [Roles and Groups](/docs/management/roles-and-groups#permissions).

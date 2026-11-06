# Connect to Suvereo's API

Once you have the API token of a [service account](/docs/connect/manage-api-keys), you can call Suvereo's API. Programmatic access, such as scripts and other systems, uses a service account. Requests made with a person's login use a different header, see [Signing In and Token Refresh](/docs/connect/signing-in).

Every request carries the token in the `Authorization` header:

```
Authorization: Token <API_TOKEN>
```

The service account can only do what its [roles](/docs/management/roles-and-groups) allow.

## Trying out the API Using Swagger UI

### Authorization

1. In the main sidebar, click **Help** → **API Documentation**. Swagger UI opens in a new tab.
2. In Swagger UI, click **Authorize** in the top-right corner.
3. Enter `Token <API_TOKEN>` in the authorization field and click **Authorize**.

You can now interact with the API.

## Navigating the Endpoints

Swagger UI lists the endpoints organized by functionality. You can test an endpoint directly from your browser using the **Try it out** feature.

### Example: Retrieving Data Sets with GET /api/data_sets

1. Find the `GET /api/data_sets` endpoint in the list.
2. Expand the endpoint by clicking on it.
3. Click **Try it out**.
4. Click **Execute** to send the request.

## Using `curl`

To authenticate with `curl`, include the API token in the header of each request. Replace `<API_TOKEN>` with your token and `<PATH>` with the endpoint path.

- **GET and DELETE requests:**

  ```bash
  curl -X 'GET' \
    'http://localhost:8000/api/<PATH>' \
    -H 'accept: application/json' \
    -H 'Authorization: Token <API_TOKEN>'
  ```

- **POST, PUT and PATCH requests:**

  ```bash
  curl -X 'POST' \
    'http://localhost:8000/api/<PATH>' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Token <API_TOKEN>' \
    -d '{
      "key": "value"
    }'
  ```

Example:

```bash
curl -X 'GET' \
  'http://localhost:8000/api/data_sets' \
  -H 'accept: application/json' \
  -H 'Authorization: Token <API_TOKEN>'
```

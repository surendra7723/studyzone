# API Documentation Clean Code Guide

## 1. Overview

This guide establishes clean code principles for API documentation in the Studyzone backend. The project uses **drf-spectacular 0.27.0** to generate **OpenAPI 3.0** schemas, which are served via:

- **Swagger UI** at `api/docs/swagger/`
- **Redoc** at `api/docs/redoc/`
- **Raw OpenAPI schema** at `api/schema/`

Documentation is not an afterthought. Every view, serializer, and endpoint must expose accurate, consistent metadata so that consumers can trust and navigate the API without reading source code.

---

## 2. Current Project Configuration

### 2.1 Settings (`config/settings.py`)

```python
INSTALLED_APPS = [
    ...
    "drf_spectacular",
    ...
]

REST_FRAMEWORK = {
    ...
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    ...
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Studyzone API",
    "DESCRIPTION": "API documentation for the Studyzone backend.",
    "VERSION": "1.0.0",
}
```

### 2.2 URL Routes (`config/urls.py`)

```python
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    ...
]
```

---

## 3. Step-by-Step: Adding Clean Documentation to an Endpoint

### Step 1: Import `extend_schema` and relevant OpenAPI types

```python
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
```

### Step 2: Annotate the view with `@extend_schema`

Provide:
- `summary`: a concise, imperative title (≤ 60 characters).
- `description`: a multi-sentence explanation of behavior, side effects, and auth requirements.
- `request`: the serializer class used for input.
- `responses`: explicit mapping of HTTP status codes to serializer schemas.
- `examples`: concrete request/response payloads.

```python
from rest_framework import status, viewsets
from drf_spectacular.utils import extend_schema, OpenApiExample

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @extend_schema(
        summary="Register a new user",
        description=(
            "Creates a new user account with email or phone verification. "
            "Returns 201 with user data and issued tokens. "
            "Requires no authentication."
        ),
        request=UserRegistrationSerializer,
        responses={
            status.HTTP_201_CREATED: UserSerializer,
            status.HTTP_400_BAD_REQUEST: serializers.ErrorResponse,
        },
        examples=[
            OpenApiExample(
                "Valid registration payload",
                value={
                    "username": "jdoe",
                    "email": "jdoe@example.com",
                    "password": "SecurePass123!",
                    "password_confirm": "SecurePass123!",
                    "verification_options": "email",
                },
                status_codes=["201"],
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
```

### Step 3: Document query parameters and headers

Use `OpenApiParameter` for filters, pagination, and search:

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="search",
            description="Case-insensitive search across username and email.",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="ordering",
            description="Field to order by. Prefix with '-' for descending.",
            required=False,
            type=str,
            enum=["username", "email", "-username", "-email"],
        ),
    ]
)
def list(self, request, *args, **kwargs):
    return super().list(request, *args, **kwargs)
```

### Step 4: Reuse response schemas across endpoints

Define shared response shapes once in a central location:

```python
# core/serializers.py
class TokenResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    user = UserSerializer()
    tokens = serializers.DictField(child=serializers.CharField())
```

```python
# apps/user/views.py
@extend_schema(
    responses={
        status.HTTP_200_OK: TokenResponseSerializer,
        status.HTTP_401_UNAUTHORIZED: serializers.ErrorResponse,
    }
)
def login(self, request, *args, **kwargs):
    ...
```

### Step 5: Verify locally

```bash
# Validate schema correctness
python manage.py spectacular --validate --fail-on-warn

# Generate schema file
python manage.py spectacular --file schema.yml
```

---

## 4. Clean Code Principles for API Documentation

### 4.1 Consistency

- Use the same response schema for identical payload shapes across endpoints.
- Always document the same status codes in the same order: 2xx first, then 4xx, then 5xx.
- Use exact enum values for `choice` and `enum` fields; never hardcode strings in descriptions.

### 4.2 Accuracy

- The `request` parameter must match the actual serializer used by the view.
- Every status code listed in `responses` must be actually returned by the view logic.
- Examples must be valid against the serializer definition (correct field names, types, and constraints).

### 4.3 Clarity

- `summary` is a title, not a sentence. Use noun phrases: "Create task", "List user profiles".
- `description` explains *what* happens, *why*, and *who* can call it.
- Avoid jargon in consumer-facing docs. Assume the reader is a frontend developer, not a backend engineer.

### 4.4 Maintainability

- Centralize error response schemas (`ErrorResponse`, `ValidationErrorResponse`) in `core/serializers.py`.
- Reuse `OpenApiExample` objects for common patterns (e.g., paginated lists, token responses).
- If a view changes, update its schema immediately in the same commit.

---

## 5. Redoc-Specific Best Practices

Redoc renders the schema differently from Swagger UI. To optimize for Redoc:

| Guideline | Rationale |
|-----------|-----------|
| Provide rich `description` fields | Redoc surfaces descriptions prominently. |
| Use `@extend_schema` on every viewset action | drf-spectacular auto-generates names from method names, which are often unclear. |
| Document `enum` constraints explicitly | Redoc renders them as dropdowns. |
| Group endpoints by URL prefix in the schema title or tags | Redoc groups by tag, so tag viewsets consistently. |
| Avoid overly long `summary` text | Redoc truncates long strings in the sidebar. |

---

## 6. Serializer Documentation

### 6.1 Field-Level Help Text

Add `help_text` to serializer fields so that generated docs include descriptions:

```python
class TaskSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        max_length=200,
        help_text="Short title of the task. Must be unique per user.",
    )
    status = serializers.ChoiceField(
        choices=Task.STATUS_CHOICES,
        help_text="Current workflow status of the task.",
    )

    class Meta:
        model = Task
        fields = ["id", "title", "status", "due_date", "created_at"]
```

### 6.2 Read-Only vs Write-Only

Explicitly mark fields with `read_only=True` or `write_only=True`. drf-spectacular surfaces this in the schema, preventing consumer confusion.

```python
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
```

---

## 7. Authentication Documentation

Document authentication schemes clearly. The project uses JWT and Session auth:

```python
# config/settings.py
SPECTACULAR_SETTINGS = {
    ...
    "COMPONENT_SECURITY_SCHEMES": {
        "JWT": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "Session": {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
        },
    },
    "SECURITY": [
        {"JWT": []},
        {"Session": []},
    ],
}
```

Then annotate public endpoints to explicitly opt out:

```python
@extend_schema(
    security=[],
    ...
)
def create(self, request, *args, **kwargs):
    ...
```

---

## 8. Versioning and Deprecation

When deprecating an endpoint:

```python
@extend_schema(
    deprecated=True,
    description="Use `/api/v2/tasks/` instead. Will be removed in version 2.0.",
    ...
)
```

This renders a "Deprecated" badge in both Swagger UI and Redoc.

---

## 9. Review Checklist

See [`docs/checklists/api-documentation-review.md`](docs/checklists/api-documentation-review.md) for the full structured review process.

---

## 10. Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Schema fails validation (`--fail-on-warn`) | Check for missing `request` or `responses` on `extend_schema`. |
| Examples do not match serializer | Run `python manage.py spectacular --file schema.yml` and inspect the examples. |
| Redoc sidebar shows raw view names | Add `summary` and `description` to every `@extend_schema`. |
| `enum` fields show as free text | Add explicit `enum` or use DRF `ChoiceField`. |
| Auth requirements are unclear | Add `security` or `security=[]` to every endpoint. |
| Duplicate response schemas | Extract shared shapes into `core/serializers.py`. |

from rest_framework.permissions import IsAuthenticatedOrReadOnly

# Re-export a project-scoped name for convenience and to keep this module useful
IsAuthenticatedOrReadOnlyPermission = IsAuthenticatedOrReadOnly

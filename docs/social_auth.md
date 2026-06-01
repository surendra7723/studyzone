# Social Auth Frontend Contract

This document describes the minimal frontend contract for the social authentication endpoints.

Base URL: /api/users/

1) Google Sign-in
- Endpoint: POST /api/users/auth/google/
- Request JSON:
  {
    "id_token": "<ujn>"
  }
- Successful Response (200):
  {
    "requires_confirmation": false,
    "tokens": {"access": "<jwt-access>", "refresh": "<jwt-refresh>"}
  }
- When an existing account exists with the same email and confirmation is required, response will still be 200 and include `requires_confirmation: true` and an explanatory `detail` field. The frontend should show a confirmation flow instructing the user to check their email for a link or token.

2) Facebook Sign-in
- Endpoint: POST /api/users/auth/facebook/
- Request JSON:
  {
    "access_token": "<facebook-access-token>"
  }
- Successful Response (200):
  {
    "tokens": {"access": "<jwt-access>", "refresh": "<jwt-refresh>"}
  }
- If an email collision requires explicit linking confirmation, response can include `requires_confirmation: true` with a `detail` message, similar to Google.
- Note: The backend validates the access token with Facebook's Graph API and (in production) requires `FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET` to be configured.

3) Confirm Social Link (email collision flow)
- Endpoint: POST /api/users/confirm-social-link/
- Request JSON:
  {
    "token": "<confirmation-token>"
  }
- Successful Response (200):
  {
    "tokens": {"access": "<jwt-access>", "refresh": "<jwt-refresh>"}
  }

4) Linked Accounts (for authenticated users)
- List: GET /api/users/linked-accounts/ -> returns array of linked providers and metadata
- Link: POST /api/users/linked-accounts/ with provider-specific payload
  - Google: {"provider": "google", "id_token": "..."}
  - Facebook: {"provider": "facebook", "access_token": "..."}
- Unlink: DELETE /api/users/linked-accounts/{provider}/

Notes & Recommendations:
- The frontend should never assume token formats beyond treating them as opaque strings.
- For Google, prefer using Google Sign-In client to obtain the `id_token` (one-time JWT) and send it to the backend.
- For Facebook, obtain a short-lived access token from the Facebook SDK and send it to the backend; the backend performs debug_token validation.
- On `requires_confirmation: true`, present a UI that explains an email was sent with a confirmation link or token. The frontend may POST the extracted token to `/confirm-social-link/`.
- Handle 4xx responses by surfacing friendly messages. Do not reveal internal validation details.

If you want, I can add code snippets to show example fetch/axios calls for each flow.
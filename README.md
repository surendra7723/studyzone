# studyzone

## Local email testing with Mailpit

The project is configured to use SMTP on `localhost:1025` by default, which matches Mailpit's local server.

Start Mailpit before registering a user with an email address, then open the Mailpit UI at `http://localhost:8025` to inspect the message.

You can override the mail settings with these environment variables if needed:

- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `EMAIL_USE_SSL`
- `DEFAULT_FROM_EMAIL`

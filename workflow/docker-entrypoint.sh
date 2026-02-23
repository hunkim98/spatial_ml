#!/bin/bash

echo "Container is running!"

# Authenticate gcloud using service account if credentials are provided
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "Authenticating with GCP using service account..."
    gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"

    # Extract project ID from service account key file
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        PROJECT_ID=$(cat "$GOOGLE_APPLICATION_CREDENTIALS" | grep -o '"project_id"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        if [ -n "$PROJECT_ID" ]; then
            echo "Setting GCP project to: $PROJECT_ID"
            gcloud config set project "$PROJECT_ID"

            # Export as environment variable for Python scripts
            export GCP_PROJECT="$PROJECT_ID"

            # Persist to bashrc so it's available in interactive shell
            echo "export GCP_PROJECT=\"$PROJECT_ID\"" >> ~/.bashrc
        fi
    fi
fi

# Activate the virtual environment
source /.venv/bin/activate

# Add venv activation to bashrc for interactive sessions
echo "source /.venv/bin/activate" >> ~/.bashrc

# Keep the container running with an interactive shell
exec /bin/bash

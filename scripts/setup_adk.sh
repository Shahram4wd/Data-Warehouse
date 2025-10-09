#!/bin/bash
# DataHub ADK Quick Setup Script
# This script helps automate the GCP and ADK setup process

set -e

echo "=== DataHub Google ADK Setup ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✓ gcloud CLI is installed${NC}"

# Get project ID
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-datahub}"
read -p "Enter GCP Project ID [$PROJECT_ID]: " input_project
PROJECT_ID="${input_project:-$PROJECT_ID}"

echo ""
echo -e "${YELLOW}Using project: $PROJECT_ID${NC}"

# Check if project exists, if not create it
if ! gcloud projects describe $PROJECT_ID &> /dev/null; then
    echo -e "${YELLOW}Project doesn't exist. Creating...${NC}"
    read -p "Enter project name [DataHub AI Agents]: " project_name
    project_name="${project_name:-DataHub AI Agents}"
    gcloud projects create $PROJECT_ID --name="$project_name"
    echo -e "${GREEN}✓ Project created${NC}"
fi

# Set current project
echo "Setting current project..."
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✓ Project set${NC}"

# Get region
REGION="${GOOGLE_CLOUD_LOCATION:-us-west1}"
read -p "Enter region [$REGION]: " input_region
REGION="${input_region:-$REGION}"

echo ""
echo -e "${YELLOW}Enabling required APIs...${NC}"

# Enable required APIs
apis=(
    "aiplatform.googleapis.com"
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
)

for api in "${apis[@]}"; do
    echo "Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID
    echo -e "${GREEN}✓ $api enabled${NC}"
done

echo ""
echo -e "${YELLOW}Setting up service account...${NC}"

# Create service account
SERVICE_ACCOUNT="datahub-adk"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL --project=$PROJECT_ID &> /dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create $SERVICE_ACCOUNT \
        --display-name="DataHub ADK Service Account" \
        --project=$PROJECT_ID
    echo -e "${GREEN}✓ Service account created${NC}"
else
    echo -e "${GREEN}✓ Service account already exists${NC}"
fi

# Grant permissions
echo "Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/aiplatform.user" \
    --quiet

echo -e "${GREEN}✓ Permissions granted${NC}"

# Create credentials directory
echo ""
echo "Creating credentials directory..."
mkdir -p .google

# Create and download credentials
echo "Downloading service account credentials..."
gcloud iam service-accounts keys create .google/credentials.json \
    --iam-account=$SERVICE_ACCOUNT_EMAIL \
    --project=$PROJECT_ID

echo -e "${GREEN}✓ Credentials saved to .google/credentials.json${NC}"

# Update .env file
echo ""
echo "Updating .env file..."

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Update or add ADK configuration
if grep -q "GOOGLE_CLOUD_PROJECT" .env; then
    # Update existing values
    sed -i "s/^GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=$PROJECT_ID/" .env
    sed -i "s/^GOOGLE_CLOUD_LOCATION=.*/GOOGLE_CLOUD_LOCATION=$REGION/" .env
else
    # Add new values
    echo "" >> .env
    echo "# Google ADK Configuration for DataHub AI Agents" >> .env
    echo "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" >> .env
    echo "GOOGLE_CLOUD_LOCATION=$REGION" >> .env
    echo "GOOGLE_GENAI_USE_VERTEXAI=True" >> .env
    echo "GOOGLE_APPLICATION_CREDENTIALS=/app/.google/credentials.json" >> .env
fi

echo -e "${GREEN}✓ .env file updated${NC}"

# Set application default credentials
echo ""
echo "Setting up application default credentials..."
gcloud auth application-default login --quiet

echo -e "${GREEN}✓ Application default credentials set${NC}"

# Verify Vertex AI access
echo ""
echo "Verifying Vertex AI access..."
if gcloud ai models list --region=$REGION --project=$PROJECT_ID &> /dev/null; then
    echo -e "${GREEN}✓ Vertex AI access verified${NC}"
else
    echo -e "${YELLOW}⚠ Could not verify Vertex AI access. This might be okay if the region doesn't support model listing.${NC}"
fi

echo ""
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo ""
echo "Next steps:"
echo "1. Build Docker containers: docker-compose build"
echo "2. Start services: docker-compose up -d"
echo "3. Access ADK web UI: http://localhost:7860"
echo ""
echo "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Credentials: .google/credentials.json"
echo ""
echo "For more information, see docs/AI/SETUP_GUIDE.md"

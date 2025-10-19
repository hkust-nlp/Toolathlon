#!/bin/bash

# Google Cloud API Services Enablement Script
# This script enables all the necessary Google Cloud APIs for Toolathlon

# first detect if the `gcloud` command is available
if ! command -v gcloud &> /dev/null; then
    echo "gcloud could not be found, please install via `curl https://sdk.cloud.google.com | bash`"
    exit 1
fi

# echo you may need to run `gcloud auth login` to login first
# then run `gcloud config set project YOUR_PROJECT_ID` to set the project

# echo how to use this script if the user does not provide a project id
if [ -z "$1" ]; then
echo "How to use this script:"
echo "bash $0 <PROJECT_ID>"
echo "Example: bash $0 toolathlon-443918"
exit 1
fi

PROJECT_ID=$1

echo "Project ID: $PROJECT_ID"

# Check if already logged in to Google Cloud, if not, perform login
if ! gcloud auth list --format="value(account)" | grep -q .; then
    echo "No logged-in account detected, logging in to Google Cloud..."
    gcloud auth login
else
    echo "Google Cloud account already logged in, no need to log in again."
fi

# set project
gcloud config set project $PROJECT_ID
echo "Project ID: $(gcloud config get-value project)"
echo ""

echo "Starting Google Cloud API services enablement for project: $PROJECT_ID"
echo "Project: $(gcloud config get-value project)"
echo ""

echo "Enabling Google Cloud API services..."
echo ""

# display enabled apis before enabling
echo "Enabled APIs:"
gcloud services list --enabled
echo ""

# Core Google APIs
echo "Enabling core Google APIs..."
gcloud services enable youtube.googleapis.com            # YouTube Data API v3
gcloud services enable gmail.googleapis.com              # Gmail API
gcloud services enable sheets.googleapis.com             # Google Sheets API
gcloud services enable calendar-json.googleapis.com      # Google Calendar API
gcloud services enable drive.googleapis.com              # Google Drive API
gcloud services enable forms.googleapis.com              # Google Forms API

# Analytics and BigQuery APIs
echo "Enabling Analytics and BigQuery APIs..."
gcloud services enable analyticshub.googleapis.com       # Analytics Hub API
gcloud services enable bigquery.googleapis.com           # BigQuery API
gcloud services enable bigqueryconnection.googleapis.com # BigQuery Connection API
gcloud services enable bigquerydatapolicy.googleapis.com # BigQuery Data Policy API
gcloud services enable bigquerymigration.googleapis.com  # BigQuery Migration API
gcloud services enable bigqueryreservation.googleapis.com # BigQuery Reservation API
gcloud services enable bigquerystorage.googleapis.com    # BigQuery Storage API

# Cloud Platform APIs
echo "Enabling Cloud Platform APIs..."
gcloud services enable dataplex.googleapis.com           # Cloud Dataplex API
gcloud services enable datastore.googleapis.com          # Cloud Datastore API
gcloud services enable logging.googleapis.com            # Cloud Logging API
gcloud services enable monitoring.googleapis.com         # Cloud Monitoring API
gcloud services enable oslogin.googleapis.com            # Cloud OS Login API
gcloud services enable sqladmin.googleapis.com           # Cloud SQL
gcloud services enable storage.googleapis.com            # Cloud Storage
gcloud services enable storage-component.googleapis.com  # Cloud Storage API
gcloud services enable cloudtrace.googleapis.com         # Cloud Trace API
gcloud services enable compute.googleapis.com            # Compute Engine API

# Search and Maps APIs
echo "Enabling Search and Maps APIs..."
gcloud services enable customsearch.googleapis.com       # Custom Search API
gcloud services enable directions-backend.googleapis.com # Directions API
gcloud services enable distance-matrix-backend.googleapis.com # Distance Matrix API
gcloud services enable mapsgrounding.googleapis.com      # Maps Grounding API
gcloud services enable places-backend.googleapis.com     # Places API
gcloud services enable routes.googleapis.com             # Routes API
gcloud services enable geocoding-backend.googleapis.com                     # Geocoding API
gcloud services enable elevation-backend.googleapis.com                     # Elevation API

# Data and Document APIs
echo "Enabling Data and Document APIs..."
gcloud services enable dataform.googleapis.com           # Dataform API
gcloud services enable driveactivity.googleapis.com      # Drive Activity API
gcloud services enable docs.googleapis.com               # Google Docs API
gcloud services enable slides.googleapis.com             # Google Slides API

# Service Management APIs
echo "Enabling Service Management APIs..."
gcloud services enable privilegedaccessmanager.googleapis.com # Privileged Access Manager API
gcloud services enable servicemanagement.googleapis.com  # Service Management API
gcloud services enable serviceusage.googleapis.com       # Service Usage API

# display enabled apis after enabling
echo "Enabled APIs:"
gcloud services list --enabled
echo ""

echo ""
echo "All Google Cloud API services have been enabled successfully!"
echo "You can verify enabled services with: gcloud services list --enabled"

### NOTE: not all apis mentioned above are necessary

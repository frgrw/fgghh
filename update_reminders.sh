source virtualenv/bin/activate
pip install -r update_reminders_requirements.txt > /dev/null
GCP_PROJECT="$(cat .gcp_project_id)" GCP_REGION="$(cat .gcp_location)" python update_reminders.py
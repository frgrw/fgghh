source virtualenv/bin/activate
pip install -r requirements.txt
pip install -r update_reminders_requirements.txt
GCP_PROJECT="test" GCP_REGION="test" python -m unittest
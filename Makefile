update_reminders: virtualenv
	GOOGLE_APPLICATION_CREDENTIALS=".gcp_credentials.json" bash ./update_reminders.sh

deploy: test
	gcloud functions deploy email_cloud_function \
	 --runtime python37 \
	 --trigger-topic reminders-topic \
	 --project $(shell cat .gcp_project_id) \
	 --region $(shell cat .gcp_location) \
	 --set-env-vars SENDGRID_API_KEY="$(shell cat .sendgrid_key)"

setup:
	gcloud app create --project $(shell cat .gcp_project_id) --region $(shell cat .gcp_location)
	gcloud iam service-accounts create --project $(shell cat .gcp_project_id) reminders-service-account --display-name "reminders service account"
	gcloud iam service-accounts keys create --project $(shell cat .gcp_project_id) ./.gcp_credentials.json --iam-account reminders-service-account@$(shell cat .gcp_project_id).iam.gserviceaccount.com
	gcloud projects add-iam-policy-binding $(shell cat .gcp_project_id) \
      --member serviceAccount:reminders-service-account@$(shell cat .gcp_project_id).iam.gserviceaccount.com \
      --role roles/cloudscheduler.admin

virtualenv:
	python3 -m venv virtualenv

test: virtualenv
	bash ./test.sh

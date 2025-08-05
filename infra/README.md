# Infrastructure Setup (Terraform)

This folder contains Terraform code to provision:
- Azure Resource Group
- Azure Container Registry (ACR)
- Azure Container Instance (ACI) to run the content pipeline

## Steps
1. Update `<ACR_LOGIN_SERVER>`, `<YOUR_AZURE_OPENAI_ENDPOINT>`, and `<YOUR_AZURE_OPENAI_KEY>` in `main.tf` after deploying ACR and OpenAI resources.
2. Build and push your pipeline container to ACR.
3. Run `terraform init && terraform apply` in this folder.

## Notes
- The container will run your Python pipeline on a schedule or on demand.
- You can add more environment variables as needed for secrets/config.

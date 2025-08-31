# Infrastructure Setup (Terraform)

This folder contains Terraform code to provision:
- Azure Resource Group
- Azure Container Apps (consumption tier, public network)
- Azure Key Vault (public access)
- Azure Storage Account (public access)
- Azure Container Instance (ACI) to run the content pipeline

## Steps
1. Build and push your pipeline container to ACR (Azure Container Registry login server is configured automatically).
2. Run `terraform init && terraform apply` in this folder.
3. Container apps will authenticate with Azure OpenAI using managed identity (no API keys required).

## Notes
- The container will run your Python pipeline on a schedule or on demand.
- You can add more environment variables as needed for secrets/config.
- Network configuration simplified for Container Apps Consumption tier compatibility.

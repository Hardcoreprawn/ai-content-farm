# Hot Topics Feed - Architecture Overview

## Workflow

1. **Womble Service** (runs daily)
   - Scrapes trending post titles/content from sources (e.g., Reddit).
   - Stores raw data in Azure Storage (Blob/Table/Cosmos DB).

2. **Content Generation Service**
   - Picks up new items from storage.
   - Uses Azure OpenAI (text + DALL-E) to generate articles and images.
   - Stores drafts (markdown + images) in a "pending approval" area (e.g., Blob Storage or GitHub PR).

3. **Approval Workflow**
   - You review drafts via GitHub PR or web UI.
   - On approval, articles/images are published (e.g., merged to main branch, triggers static site build).

4. **Static Site Build/Publish**
   - Approved content triggers a site build (GitHub Actions, Azure Static Web Apps, etc.).
   - New articles go live.

## Security
- All secrets are stored in Azure Key Vault.
- Managed identities are used for service-to-service authentication.
- No secrets in code or environment variables.

---

# Step 1: Womble - Get Topics and Store Them
- Scrape trending topics from Reddit (or other sources).
- Store the results in Azure Table Storage (or Blob/Cosmos DB) as raw, unprocessed data for later processing.

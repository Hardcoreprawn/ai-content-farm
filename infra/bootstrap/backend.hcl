# Bootstrap Backend Configuration
# This should be used AFTER the bootstrap has created the storage account
# and you want to migrate from local state to remote state

storage_account_name = "aicontentfarm76ko2h"
container_name       = "tfstate"
key                  = "bootstrap.tfstate"
resource_group_name  = "ai-content-farm-bootstrap"

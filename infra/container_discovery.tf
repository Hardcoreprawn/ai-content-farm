# Dynamic Container Discovery Data Source with Fallback
# This data source discovers all valid containers from the containers/ directory
# and generates container image URLs with intelligent fallback logic

data "external" "container_discovery" {
  program = ["${path.module}/../scripts/terraform-discover-containers-with-fallback.sh"]

  # Pass variables as environment variables
  query = {
    image_tag               = var.image_tag
    image_fallback_strategy = var.image_fallback_strategy
  }
}

# Container images are returned directly from the discovery script
locals {
  # The fallback script returns the complete container image map
  container_images = data.external.container_discovery.result
}

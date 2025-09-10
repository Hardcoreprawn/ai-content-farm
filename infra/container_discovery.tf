# Dynamic Container Discovery Data Source
# This data source discovers all valid containers from the containers/ directory
# and generates the appropriate container image URLs

data "external" "container_discovery" {
  program = ["${path.module}/../scripts/terraform-discover-containers.sh"]
}

# Transform the discovered container list into a map of container images
locals {
  # Parse the comma-separated string from the discovery script
  discovered_containers = split(",", data.external.container_discovery.result.containers)

  # Generate container image map from discovered containers
  discovered_container_images = {
    for container in local.discovered_containers :
    container => "ghcr.io/hardcoreprawn/ai-content-farm/${container}:${var.image_tag}"
  }

  # Use discovered containers, but allow var.container_images to override
  container_images = merge(local.discovered_container_images, var.container_images)
}

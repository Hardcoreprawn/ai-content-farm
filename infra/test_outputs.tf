# Test output to verify dynamic container discovery with fallback
output "discovered_container_images" {
  value = data.external.container_discovery.result
}

output "container_images" {
  value = local.container_images
}

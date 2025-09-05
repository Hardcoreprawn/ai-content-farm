#!/bin/bash

echo "[BUILD] Testing multi-stage Docker builds..."

build_failures=0
containers_tested=0

# Test containers with multi-stage builds
test_containers=("content-processor" "content-collector" "site-generator")

for container_name in "${test_containers[@]}"; do
  container_dir="containers/$container_name"

  if [ -d "$container_dir" ] && [ -f "$container_dir/Dockerfile" ]; then
    containers_tested=$((containers_tested + 1))
    echo "[BUILD] Testing $container_name development build..."

    # Test development build
    if docker build -f "$container_dir/Dockerfile" --target development -t "$container_name:dev" .; then
      echo "[PASS] $container_name development build successful"

      # Test production build
      echo "[BUILD] Testing $container_name production build..."
      if docker build -f "$container_dir/Dockerfile" --target production -t "$container_name:prod" .; then
        echo "[PASS] $container_name production build successful"

        # Show image sizes
        echo "[INFO] Image sizes:"
        docker images "$container_name" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
      else
        echo "[FAIL] $container_name production build failed"
        build_failures=$((build_failures + 1))
      fi
    else
      echo "[FAIL] $container_name development build failed"
      build_failures=$((build_failures + 1))
    fi
  else
    echo "[WARN] Skipping $container_name - no Dockerfile found"
  fi
done

# Generate summary
success_rate=0
if [ $containers_tested -gt 0 ]; then
  success_rate=$(( (containers_tested - build_failures) * 100 / containers_tested ))
fi

echo ""
echo "[STATS] Build Summary:"
echo "- Containers tested: $containers_tested"
echo "- Build failures: $build_failures"
echo "- Success rate: $success_rate%"

if [ "$build_failures" -gt 0 ]; then
  echo "[FAIL] $build_failures container(s) failed to build"
  exit 1
else
  echo "[PASS] All containers build successfully"
fi

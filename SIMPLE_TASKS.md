# TODO

## Fix deployment
- [x] Run `scripts/fix-oidc-environment-credentials.sh`
- [x] Grant Azure permissions to OIDC service principal  
- [ ] Grant Azure AD application creation permissions
- [ ] Import existing resource group to Terraform state
- [ ] Deploy to staging
- [ ] Test content generation works

## Clean up scripts
- [ ] Delete duplicate setup scripts
- [ ] Fix Makefile
- [ ] Test clean setup

## Add tests
- [ ] Unit tests for functions
- [ ] End-to-end test
- [ ] Add to CI/CD

## Plan improvements
- [ ] Split up GetHotTopics function
- [ ] Design better content pipeline
- [ ] Research MCP integration

## Maintenance
- [ ] Update Terraform version (currently 1.12.2) quarterly
- [ ] Update GitHub Actions versions quarterly
- [ ] Update Python dependencies monthly

# Infrastructure as Code (Terraform)

Provisions the Stage 1 infrastructure (Milvus standalone + its etcd/minio
dependencies, and optionally the chatbot app container) using Docker, via
the `kreuzwerker/docker` provider. This mirrors `docker-compose.yml` as
code, and can be swapped for a cloud provider later by changing the
provider block and resources.

## Prerequisites
- Terraform >= 1.5
- Docker running locally

## Usage

```bash
cd terraform
terraform init
terraform plan -var="openai_api_key=sk-..."
terraform apply -var="openai_api_key=sk-..." -var="deploy_app_container=true"
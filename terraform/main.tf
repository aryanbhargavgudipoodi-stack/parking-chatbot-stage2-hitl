terraform {
  required_version = ">= 1.5.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_network" "parking_net" {
  name = "parking-chatbot-net"
}

resource "docker_volume" "etcd_data" {
  name = "parking-etcd-data"
}

resource "docker_volume" "minio_data" {
  name = "parking-minio-data"
}

resource "docker_volume" "milvus_data" {
  name = "parking-milvus-data"
}

resource "docker_image" "etcd" {
  name = "quay.io/coreos/etcd:v3.5.5"
}

resource "docker_image" "minio" {
  name = "minio/minio:RELEASE.2023-03-20T20-16-18Z"
}

resource "docker_image" "milvus" {
  name = "milvusdb/milvus:v2.3.3"
}

resource "docker_container" "etcd" {
  name  = "parking-etcd"
  image = docker_image.etcd.image_id
  networks_advanced {
    name = docker_network.parking_net.name
  }
  env = [
    "ETCD_AUTO_COMPACTION_MODE=revision",
    "ETCD_AUTO_COMPACTION_RETENTION=1000",
    "ETCD_QUOTA_BACKEND_BYTES=4294967296",
    "ETCD_SNAPSHOT_COUNT=50000",
  ]
  command = [
    "etcd", "-advertise-client-urls=http://127.0.0.1:2379",
    "-listen-client-urls", "http://0.0.0.0:2379", "--data-dir", "/etcd",
  ]
  volumes {
    volume_name    = docker_volume.etcd_data.name
    container_path = "/etcd"
  }
}

resource "docker_container" "minio" {
  name  = "parking-minio"
  image = docker_image.minio.image_id
  networks_advanced {
    name = docker_network.parking_net.name
  }
  env = [
    "MINIO_ACCESS_KEY=minioadmin",
    "MINIO_SECRET_KEY=minioadmin",
  ]
  command = ["minio", "server", "/minio_data", "--console-address", ":9001"]
  volumes {
    volume_name    = docker_volume.minio_data.name
    container_path = "/minio_data"
  }
}

resource "docker_container" "milvus" {
  name  = "parking-milvus"
  image = docker_image.milvus.image_id
  networks_advanced {
    name = docker_network.parking_net.name
  }
  env = [
    "ETCD_ENDPOINTS=parking-etcd:2379",
    "MINIO_ADDRESS=parking-minio:9000",
  ]
  command = ["milvus", "run", "standalone"]
  volumes {
    volume_name    = docker_volume.milvus_data.name
    container_path = "/var/lib/milvus"
  }
  ports {
    internal = 19530
    external = var.milvus_port
  }
  ports {
    internal = 9091
    external = 9091
  }
  depends_on = [docker_container.etcd, docker_container.minio]
}

resource "docker_image" "chatbot_app" {
  name = "parking-chatbot:latest"
  build {
    context = "${path.module}/.."
  }
}

resource "docker_container" "chatbot_app" {
  count = var.deploy_app_container ? 1 : 0
  name  = "parking-chatbot-app"
  image = docker_image.chatbot_app.image_id
  networks_advanced {
    name = docker_network.parking_net.name
  }
  env = [
    "MILVUS_HOST=parking-milvus",
    "MILVUS_PORT=19530",
    "OPENAI_API_KEY=${var.openai_api_key}",
    "VECTOR_BACKEND=milvus",
  ]
  depends_on = [docker_container.milvus]
}
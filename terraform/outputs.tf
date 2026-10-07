output "milvus_endpoint" {
  value = "localhost:${var.milvus_port}"
}

output "network_name" {
  value = docker_network.parking_net.name
}
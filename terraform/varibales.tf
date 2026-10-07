variable "openai_api_key" {
  description = "OpenAI API key injected into the chatbot container"
  type        = string
  sensitive   = true
  default     = ""
}

variable "milvus_port" {
  description = "Host port mapped to Milvus's 19530"
  type        = number
  default     = 19530
}

variable "deploy_app_container" {
  description = "Whether to also build & run the chatbot app container"
  type        = bool
  default     = false
}
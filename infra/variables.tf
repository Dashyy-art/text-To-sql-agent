variable "project_id" {
  description = "ID du projet GCP (le même que prj_data)"
  type        = string
}

variable "marts_dataset_id" {
  description = "Seul dataset que l'agent a le droit de lire"
  type        = string
  default     = "marts"
}

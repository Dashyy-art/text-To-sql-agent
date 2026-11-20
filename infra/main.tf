provider "google" {
  project = var.project_id
}

# Identité propre à l'agent : il n'utilise jamais les identifiants d'un humain.
resource "google_service_account" "agent" {
  account_id   = "sql-agent"
  display_name = "Agent text-to-SQL (lecture seule sur marts)"
}

# Droit 1 : LIRE les tables du dataset marts, et lui seul.
# Pas de droit sur raw, staging, intermediate ni audit.
resource "google_bigquery_dataset_iam_member" "agent_marts_viewer" {
  dataset_id = var.marts_dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.agent.email}"
}

# Droit 2 : LANCER des requêtes (des "jobs") dans le projet.
# Ce rôle ne donne accès à aucune donnée : il permet seulement d'exécuter.
resource "google_project_iam_member" "agent_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.agent.email}"
}

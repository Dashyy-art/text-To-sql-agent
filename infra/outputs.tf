output "agent_service_account_email" {
  description = "Email du compte de service de l'agent"
  value       = google_service_account.agent.email
}

resource "google_monitoring_alert_policy" "unauthorized_access" {
  display_name = "jurydoc-critical-unauthorized-access-alert"
  combiner     = "OR"
  
  conditions {
    display_name = "High count of 403 Forbidden responses"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"jurydoc-api\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code=\"403\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 3.0

      trigger {
        count = 1
      }
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  documentation {
    content   = "CRITICAL: Multiple 403 errors detected."
    mime_type = "text/markdown"
  }
}
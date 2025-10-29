"""
Reconciliation Dashboard

Real-time view of reconciliation status.
"""

from datetime import datetime

from workspace.features.position_reconciliation import (
    PositionReconciliationService,
)


class ReconciliationDashboard:
    """Dashboard for monitoring reconciliation"""

    def __init__(self, reconciliation_service: PositionReconciliationService):
        self.service = reconciliation_service

    def get_summary(self) -> dict:
        """Get reconciliation summary"""
        stats = self.service.get_stats()

        return {
            "is_running": stats["is_running"],
            "interval_seconds": stats["reconciliation_interval_seconds"],
            "total_reconciliations": stats["total_reconciliations"],
            "total_discrepancies": stats["total_discrepancies"],
            "total_auto_corrections": stats["total_auto_corrections"],
            "total_critical_alerts": stats["total_critical_alerts"],
            "last_check": datetime.utcnow().isoformat(),
        }

    def get_health_status(self) -> str:
        """Get health status (HEALTHY, WARNING, CRITICAL)"""
        stats = self.service.get_stats()

        if not stats["is_running"]:
            return "CRITICAL"  # Reconciliation not running

        # Check critical alerts
        if stats["total_critical_alerts"] > 0:
            return "CRITICAL"

        # Check for recent discrepancies
        if stats["total_discrepancies"] > stats["total_auto_corrections"]:
            return "WARNING"

        return "HEALTHY"

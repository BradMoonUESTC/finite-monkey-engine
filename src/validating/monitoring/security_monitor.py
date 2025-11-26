"""Security Monitoring Engine for Continuous Security Analysis.

This module provides continuous security monitoring capabilities including
metrics tracking, accuracy reporting, alerting, and performance monitoring.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional


class AlertSeverity(Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MetricType(Enum):
    """Types of metrics to track."""

    SCAN_COUNT = "scan_count"
    FINDING_COUNT = "finding_count"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    SCAN_DURATION = "scan_duration"
    CRITICAL_FINDINGS = "critical_findings"
    COVERAGE = "coverage"


@dataclass
class SecurityMetric:
    """A security metric data point."""

    metric_type: MetricType
    value: float
    timestamp: datetime
    context: Dict = field(default_factory=dict)


@dataclass
class SecurityAlert:
    """A security monitoring alert."""

    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    source: str
    timestamp: datetime
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolution: Optional[str] = None


@dataclass
class AnalysisReport:
    """A periodic analysis report."""

    report_id: str
    period_start: datetime
    period_end: datetime
    total_scans: int
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    false_positive_rate: float
    average_scan_duration: float
    coverage_percentage: float
    top_vulnerability_types: List[str]
    recommendations: List[str]


@dataclass
class PerformanceStats:
    """Performance statistics for the monitoring engine."""

    total_scans: int = 0
    total_findings: int = 0
    average_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    uptime_seconds: float = 0.0
    last_scan_time: Optional[datetime] = None
    # Running sum for more stable average calculation
    _duration_sum_ms: float = 0.0


class SecurityMonitoringEngine:
    """Continuous security monitoring capabilities.

    Features:
    - Track analysis metrics
    - Generate accuracy reports
    - Alert on high-risk findings
    - Performance monitoring
    - Trend analysis
    """

    def __init__(self) -> None:
        """Initialize the security monitoring engine."""
        self.metrics: List[SecurityMetric] = []
        self.alerts: List[SecurityAlert] = []
        self.reports: List[AnalysisReport] = []
        self.stats = PerformanceStats()
        self.start_time = datetime.now()
        self.alert_callbacks: List[Callable[[SecurityAlert], None]] = []
        self._alert_counter = 0

    def record_metric(self, metric_type: MetricType, value: float, context: Optional[Dict] = None) -> SecurityMetric:
        """Record a security metric.

        Args:
            metric_type: Type of metric
            value: Metric value
            context: Additional context

        Returns:
            The recorded metric
        """
        metric = SecurityMetric(metric_type=metric_type, value=value, timestamp=datetime.now(), context=context or {})
        self.metrics.append(metric)
        return metric

    def record_scan(self, duration_ms: float, findings_count: int, critical_count: int = 0) -> None:
        """Record a scan result.

        Args:
            duration_ms: Scan duration in milliseconds
            findings_count: Number of findings
            critical_count: Number of critical findings
        """
        now = datetime.now()

        # Update stats
        self.stats.total_scans += 1
        self.stats.total_findings += findings_count
        self.stats.last_scan_time = now

        # Update duration stats using running sum for numerical stability
        # This avoids floating point precision loss that can occur with
        # the traditional running average formula over many iterations
        self.stats._duration_sum_ms += duration_ms
        self.stats.average_duration_ms = self.stats._duration_sum_ms / self.stats.total_scans

        self.stats.max_duration_ms = max(self.stats.max_duration_ms, duration_ms)
        self.stats.min_duration_ms = min(self.stats.min_duration_ms, duration_ms)

        # Record metrics
        self.record_metric(MetricType.SCAN_COUNT, 1)
        self.record_metric(MetricType.FINDING_COUNT, findings_count)
        self.record_metric(MetricType.SCAN_DURATION, duration_ms)
        self.record_metric(MetricType.CRITICAL_FINDINGS, critical_count)

        # Create alert for critical findings
        if critical_count > 0:
            self.create_alert(
                severity=AlertSeverity.CRITICAL, title=f"Critical Findings Detected", description=f"Scan detected {critical_count} critical vulnerabilities", source="scan_engine"
            )

    def record_false_positive(self, finding_id: str) -> None:
        """Record a false positive finding.

        Args:
            finding_id: ID of the false positive finding
        """
        # Calculate and record false positive rate
        if self.stats.total_findings > 0:
            # Get count of false positives from context
            fp_metrics = [m for m in self.metrics if m.metric_type == MetricType.FALSE_POSITIVE_RATE]
            current_fps = len(fp_metrics)

            fp_rate = (current_fps + 1) / self.stats.total_findings
            self.record_metric(MetricType.FALSE_POSITIVE_RATE, fp_rate, {"finding_id": finding_id})

    def create_alert(self, severity: AlertSeverity, title: str, description: str, source: str = "monitor") -> SecurityAlert:
        """Create a security alert.

        Args:
            severity: Alert severity
            title: Alert title
            description: Alert description
            source: Source of the alert

        Returns:
            The created alert
        """
        self._alert_counter += 1
        alert = SecurityAlert(alert_id=f"ALERT-{self._alert_counter:06d}", severity=severity, title=title, description=description, source=source, timestamp=datetime.now())
        self.alerts.append(alert)

        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception:
                pass

        return alert

    def acknowledge_alert(self, alert_id: str, user: str, resolution: Optional[str] = None) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: ID of the alert
            user: User acknowledging
            resolution: Optional resolution notes

        Returns:
            True if alert was found and acknowledged
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.is_acknowledged = True
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.now()
                alert.resolution = resolution
                return True
        return False

    def register_alert_callback(self, callback: Callable[[SecurityAlert], None]) -> None:
        """Register a callback for new alerts.

        Args:
            callback: Function to call when alert is created
        """
        self.alert_callbacks.append(callback)

    def generate_report(self, period_hours: int = 24) -> AnalysisReport:
        """Generate a periodic analysis report.

        Args:
            period_hours: Report period in hours

        Returns:
            The generated report
        """
        now = datetime.now()
        period_start = now - timedelta(hours=period_hours)

        # Filter metrics for period
        period_metrics = [m for m in self.metrics if m.timestamp >= period_start]

        # Calculate statistics
        scan_metrics = [m for m in period_metrics if m.metric_type == MetricType.SCAN_COUNT]
        finding_metrics = [m for m in period_metrics if m.metric_type == MetricType.FINDING_COUNT]
        duration_metrics = [m for m in period_metrics if m.metric_type == MetricType.SCAN_DURATION]
        critical_metrics = [m for m in period_metrics if m.metric_type == MetricType.CRITICAL_FINDINGS]
        fp_metrics = [m for m in period_metrics if m.metric_type == MetricType.FALSE_POSITIVE_RATE]

        total_scans = len(scan_metrics)
        total_findings = sum(m.value for m in finding_metrics)
        critical = sum(m.value for m in critical_metrics)

        avg_duration = sum(m.value for m in duration_metrics) / len(duration_metrics) if duration_metrics else 0
        fp_rate = fp_metrics[-1].value if fp_metrics else 0.0

        # Estimate severity distribution
        high = int(total_findings * 0.2)
        medium = int(total_findings * 0.3)
        low = int(total_findings - critical - high - medium)

        report = AnalysisReport(
            report_id=f"RPT-{now.strftime('%Y%m%d%H%M%S')}",
            period_start=period_start,
            period_end=now,
            total_scans=total_scans,
            total_findings=int(total_findings),
            critical_findings=int(critical),
            high_findings=high,
            medium_findings=medium,
            low_findings=max(0, low),
            false_positive_rate=fp_rate,
            average_scan_duration=avg_duration,
            coverage_percentage=self._calculate_coverage(period_metrics),
            top_vulnerability_types=self._get_top_vuln_types(period_metrics),
            recommendations=self._generate_recommendations(critical, fp_rate),
        )

        self.reports.append(report)
        return report

    def _calculate_coverage(self, metrics: List[SecurityMetric]) -> float:
        """Calculate code coverage from metrics."""
        coverage_metrics = [m for m in metrics if m.metric_type == MetricType.COVERAGE]
        if coverage_metrics:
            return coverage_metrics[-1].value
        return 0.0

    def _get_top_vuln_types(self, metrics: List[SecurityMetric]) -> List[str]:
        """Get top vulnerability types from metrics."""
        vuln_types: Dict[str, int] = {}

        for m in metrics:
            if m.metric_type == MetricType.FINDING_COUNT and "vuln_type" in m.context:
                vtype = m.context["vuln_type"]
                vuln_types[vtype] = vuln_types.get(vtype, 0) + int(m.value)

        sorted_types = sorted(vuln_types.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_types[:5]]

    def _generate_recommendations(self, critical_count: float, fp_rate: float) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []

        if critical_count > 5:
            recommendations.append("High number of critical findings - prioritize security review")

        if fp_rate > 0.3:
            recommendations.append("False positive rate is high - consider tuning detection rules")

        if not recommendations:
            recommendations.append("Security posture appears stable")

        return recommendations

    def get_metrics_summary(self, period_hours: int = 24) -> Dict:
        """Get a summary of metrics for a period.

        Args:
            period_hours: Period in hours

        Returns:
            Metrics summary dictionary
        """
        now = datetime.now()
        period_start = now - timedelta(hours=period_hours)

        period_metrics = [m for m in self.metrics if m.timestamp >= period_start]

        return {
            "period_hours": period_hours,
            "total_metrics": len(period_metrics),
            "scans": len([m for m in period_metrics if m.metric_type == MetricType.SCAN_COUNT]),
            "findings": sum(m.value for m in period_metrics if m.metric_type == MetricType.FINDING_COUNT),
            "critical_findings": sum(m.value for m in period_metrics if m.metric_type == MetricType.CRITICAL_FINDINGS),
            "avg_duration_ms": self.stats.average_duration_ms,
        }

    def get_alert_summary(self) -> Dict:
        """Get a summary of alerts.

        Returns:
            Alert summary dictionary
        """
        unacknowledged = [a for a in self.alerts if not a.is_acknowledged]

        severity_counts = {}
        for sev in AlertSeverity:
            severity_counts[sev.value] = len([a for a in self.alerts if a.severity == sev])

        return {
            "total_alerts": len(self.alerts),
            "unacknowledged": len(unacknowledged),
            "by_severity": severity_counts,
            "recent_alerts": [
                {"id": a.alert_id, "severity": a.severity.value, "title": a.title, "timestamp": a.timestamp.isoformat()}
                for a in sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)[:5]
            ],
        }

    def get_performance_stats(self) -> Dict:
        """Get performance statistics.

        Returns:
            Performance stats dictionary
        """
        self.stats.uptime_seconds = (datetime.now() - self.start_time).total_seconds()

        return {
            "total_scans": self.stats.total_scans,
            "total_findings": self.stats.total_findings,
            "average_duration_ms": round(self.stats.average_duration_ms, 2),
            "max_duration_ms": round(self.stats.max_duration_ms, 2),
            "min_duration_ms": round(self.stats.min_duration_ms, 2) if self.stats.min_duration_ms != float("inf") else 0,
            "uptime_seconds": round(self.stats.uptime_seconds, 2),
            "last_scan": self.stats.last_scan_time.isoformat() if self.stats.last_scan_time else None,
            "findings_per_scan": round(self.stats.total_findings / self.stats.total_scans, 2) if self.stats.total_scans > 0 else 0,
        }

    def get_trend_analysis(self, period_hours: int = 168) -> Dict:
        """Get trend analysis over a period.

        Args:
            period_hours: Period in hours (default 1 week)

        Returns:
            Trend analysis dictionary
        """
        now = datetime.now()
        period_start = now - timedelta(hours=period_hours)

        # Group metrics by day
        daily_findings: Dict[str, float] = {}
        daily_criticals: Dict[str, float] = {}

        for m in self.metrics:
            if m.timestamp < period_start:
                continue

            day = m.timestamp.strftime("%Y-%m-%d")

            if m.metric_type == MetricType.FINDING_COUNT:
                daily_findings[day] = daily_findings.get(day, 0) + m.value
            elif m.metric_type == MetricType.CRITICAL_FINDINGS:
                daily_criticals[day] = daily_criticals.get(day, 0) + m.value

        # Calculate trends
        finding_values = list(daily_findings.values())
        critical_values = list(daily_criticals.values())

        finding_trend = "stable"
        if len(finding_values) >= 2:
            if finding_values[-1] > finding_values[0] * 1.2:
                finding_trend = "increasing"
            elif finding_values[-1] < finding_values[0] * 0.8:
                finding_trend = "decreasing"

        return {
            "period_hours": period_hours,
            "daily_findings": daily_findings,
            "daily_criticals": daily_criticals,
            "finding_trend": finding_trend,
            "total_findings": sum(finding_values),
            "total_criticals": sum(critical_values),
        }

    def export_metrics(self) -> List[Dict]:
        """Export all metrics as JSON-serializable list.

        Returns:
            List of metric dictionaries
        """
        return [{"type": m.metric_type.value, "value": m.value, "timestamp": m.timestamp.isoformat(), "context": m.context} for m in self.metrics]

    def clear_old_metrics(self, days: int = 30) -> int:
        """Clear metrics older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of metrics cleared
        """
        cutoff = datetime.now() - timedelta(days=days)
        old_count = len(self.metrics)
        self.metrics = [m for m in self.metrics if m.timestamp >= cutoff]
        return old_count - len(self.metrics)

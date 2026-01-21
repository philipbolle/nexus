"""
NEXUS Self-Evolution System - Performance Analyzer

Metrics collection, statistical analysis, and bottleneck detection for system optimization.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import logging
import statistics
from enum import Enum

from ..database import Database
from ..config import settings


class MetricType(Enum):
    """Types of metrics to analyze."""
    AGENT_PERFORMANCE = "agent_performance"
    API_USAGE = "api_usage"
    SYSTEM_METRICS = "system_metrics"
    COST = "cost"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"


class TrendDirection(Enum):
    """Trend direction for metrics."""
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"


class BottleneckSeverity(Enum):
    """Severity levels for detected bottlenecks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PerformanceAnalyzer:
    """Analyzes system performance and detects bottlenecks."""

    def __init__(self, database: Database):
        self.db = database
        self.logger = logging.getLogger(__name__)

    async def analyze_period(
        self,
        start_date: date,
        end_date: date,
        metric_types: Optional[List[MetricType]] = None
    ) -> Dict[str, Any]:
        """
        Analyze performance metrics for a specific time period.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            metric_types: Types of metrics to analyze (default: all)

        Returns:
            Dictionary with analysis results
        """
        if metric_types is None:
            metric_types = list(MetricType)

        analysis = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "metrics": {},
            "trends": [],
            "bottlenecks": [],
            "recommendations": []
        }

        # Analyze each metric type
        for metric_type in metric_types:
            try:
                metric_analysis = await self._analyze_metric_type(
                    metric_type, start_date, end_date
                )
                analysis["metrics"][metric_type.value] = metric_analysis

                # Extract trends and bottlenecks
                if "trend" in metric_analysis:
                    analysis["trends"].append({
                        "metric": metric_type.value,
                        **metric_analysis["trend"]
                    })

                if "bottlenecks" in metric_analysis:
                    analysis["bottlenecks"].extend(metric_analysis["bottlenecks"])

            except Exception as e:
                self.logger.error(f"Failed to analyze {metric_type}: {e}")

        # Generate overall recommendations
        analysis["recommendations"] = await self._generate_recommendations(analysis)

        return analysis

    async def _analyze_metric_type(
        self,
        metric_type: MetricType,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Analyze a specific metric type."""
        if metric_type == MetricType.AGENT_PERFORMANCE:
            return await self._analyze_agent_performance(start_date, end_date)
        elif metric_type == MetricType.API_USAGE:
            return await self._analyze_api_usage(start_date, end_date)
        elif metric_type == MetricType.SYSTEM_METRICS:
            return await self._analyze_system_metrics(start_date, end_date)
        elif metric_type == MetricType.COST:
            return await self._analyze_cost(start_date, end_date)
        elif metric_type == MetricType.LATENCY:
            return await self._analyze_latency(start_date, end_date)
        elif metric_type == MetricType.ERROR_RATE:
            return await self._analyze_error_rate(start_date, end_date)
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")

    async def _analyze_agent_performance(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Analyze agent performance metrics."""
        query = """
            SELECT
                agent_id,
                agent_name,
                date,
                total_requests,
                successful_requests,
                failed_requests,
                total_tokens,
                total_cost_usd,
                avg_latency_ms,
                p95_latency_ms,
                p99_latency_ms
            FROM agent_performance
            WHERE date BETWEEN $1 AND $2
            ORDER BY date, agent_id
        """

        rows = await self.db.fetch(query, start_date, end_date)

        if not rows:
            return {"data_available": False, "message": "No agent performance data"}

        # Process data
        agents = {}
        dates = set()
        total_requests = 0
        successful_requests = 0
        total_cost = 0.0

        for row in rows:
            agent_id = row["agent_id"]
            date_val = row["date"]
            dates.add(date_val)

            if agent_id not in agents:
                agents[agent_id] = {
                    "name": row["agent_name"],
                    "requests": [],
                    "success_rate": [],
                    "cost": [],
                    "latency": []
                }

            agents[agent_id]["requests"].append(row["total_requests"])
            agents[agent_id]["success_rate"].append(
                row["successful_requests"] / max(row["total_requests"], 1)
            )
            agents[agent_id]["cost"].append(float(row["total_cost_usd"] or 0))
            agents[agent_id]["latency"].append(row["avg_latency_ms"] or 0)

            total_requests += row["total_requests"]
            successful_requests += row["successful_requests"]
            total_cost += float(row["total_cost_usd"] or 0)

        # Calculate statistics
        agent_stats = {}
        bottlenecks = []

        for agent_id, data in agents.items():
            if not data["requests"]:
                continue

            avg_requests = statistics.mean(data["requests"])
            avg_success_rate = statistics.mean(data["success_rate"])
            avg_cost = statistics.mean(data["cost"])
            avg_latency = statistics.mean(data["latency"])

            agent_stats[agent_id] = {
                "name": data["name"],
                "avg_requests_per_day": avg_requests,
                "avg_success_rate": avg_success_rate,
                "avg_cost_per_day": avg_cost,
                "avg_latency_ms": avg_latency
            }

            # Detect bottlenecks
            if avg_success_rate < 0.8:
                bottlenecks.append({
                    "agent_id": agent_id,
                    "agent_name": data["name"],
                    "metric": "success_rate",
                    "value": avg_success_rate,
                    "threshold": 0.8,
                    "severity": BottleneckSeverity.HIGH.value
                })

            if avg_latency > 5000:  # 5 seconds
                bottlenecks.append({
                    "agent_id": agent_id,
                    "agent_name": data["name"],
                    "metric": "latency",
                    "value": avg_latency,
                    "threshold": 5000,
                    "severity": BottleneckSeverity.MEDIUM.value
                })

            if avg_cost > 1.0:  # $1 per day
                bottlenecks.append({
                    "agent_id": agent_id,
                    "agent_name": data["name"],
                    "metric": "cost",
                    "value": avg_cost,
                    "threshold": 1.0,
                    "severity": BottleneckSeverity.MEDIUM.value
                })

        # Calculate overall success rate
        overall_success_rate = successful_requests / max(total_requests, 1)

        # Detect trend
        trend = await self._detect_trend(list(dates), agents)

        return {
            "data_available": True,
            "period_days": len(dates),
            "total_agents": len(agents),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "overall_success_rate": overall_success_rate,
            "total_cost_usd": total_cost,
            "agent_statistics": agent_stats,
            "bottlenecks": bottlenecks,
            "trend": trend
        }

    async def _analyze_api_usage(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Analyze API usage patterns."""
        query = """
            SELECT
                provider,
                model_name,
                COUNT(*) as request_count,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cost_usd) as total_cost,
                AVG(latency_ms) as avg_latency
            FROM api_usage
            WHERE timestamp::date BETWEEN $1 AND $2
            GROUP BY provider, model_name
            ORDER BY total_cost DESC
        """

        rows = await self.db.fetch(query, start_date, end_date)

        if not rows:
            return {"data_available": False, "message": "No API usage data"}

        providers = {}
        total_cost = 0.0
        total_requests = 0

        for row in rows:
            provider = row["provider"]
            model = row["model_name"]
            cost = float(row["total_cost"] or 0)

            if provider not in providers:
                providers[provider] = {
                    "models": {},
                    "total_cost": 0,
                    "total_requests": 0
                }

            providers[provider]["models"][model] = {
                "request_count": row["request_count"],
                "total_input_tokens": row["total_input_tokens"],
                "total_output_tokens": row["total_output_tokens"],
                "total_cost": cost,
                "avg_latency": row["avg_latency"]
            }

            providers[provider]["total_cost"] += cost
            providers[provider]["total_requests"] += row["request_count"]

            total_cost += cost
            total_requests += row["request_count"]

        # Detect cost inefficiencies
        bottlenecks = []
        for provider, data in providers.items():
            if data["total_cost"] > total_cost * 0.5 and len(providers) > 1:
                bottlenecks.append({
                    "provider": provider,
                    "metric": "cost_concentration",
                    "value": data["total_cost"],
                    "percentage": data["total_cost"] / total_cost,
                    "threshold": 0.5,
                    "severity": BottleneckSeverity.MEDIUM.value
                })

        return {
            "data_available": True,
            "total_providers": len(providers),
            "total_requests": total_requests,
            "total_cost_usd": total_cost,
            "providers": providers,
            "bottlenecks": bottlenecks
        }

    async def _analyze_system_metrics(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Analyze system metrics (CPU, memory, disk)."""
        query = """
            SELECT
                metric_name,
                metric_value,
                collected_at
            FROM system_metrics
            WHERE collected_at::date BETWEEN $1 AND $2
            ORDER BY collected_at
        """

        rows = await self.db.fetch(query, start_date, end_date)

        if not rows:
            return {"data_available": False, "message": "No system metrics data"}

        # Group by metric name
        metrics = {}
        for row in rows:
            name = row["metric_name"]
            value = row["metric_value"]
            timestamp = row["collected_at"]

            if name not in metrics:
                metrics[name] = []

            metrics[name].append({"value": value, "timestamp": timestamp})

        # Analyze each metric
        analysis = {}
        bottlenecks = []

        for name, values in metrics.items():
            if not values:
                continue

            numeric_values = [v["value"] for v in values if isinstance(v["value"], (int, float))]
            if not numeric_values:
                continue

            avg_value = statistics.mean(numeric_values)
            max_value = max(numeric_values)
            min_value = min(numeric_values)

            analysis[name] = {
                "average": avg_value,
                "maximum": max_value,
                "minimum": min_value,
                "samples": len(values)
            }

            # Detect resource bottlenecks
            if name == "cpu_percent" and avg_value > 80:
                bottlenecks.append({
                    "metric": name,
                    "value": avg_value,
                    "threshold": 80,
                    "severity": BottleneckSeverity.MEDIUM.value
                })
            elif name == "memory_percent" and avg_value > 85:
                bottlenecks.append({
                    "metric": name,
                    "value": avg_value,
                    "threshold": 85,
                    "severity": BottleneckSeverity.HIGH.value
                })
            elif name == "disk_percent" and avg_value > 90:
                bottlenecks.append({
                    "metric": name,
                    "value": avg_value,
                    "threshold": 90,
                    "severity": BottleneckSeverity.CRITICAL.value
                })

        return {
            "data_available": True,
            "metrics_analyzed": len(analysis),
            "metric_details": analysis,
            "bottlenecks": bottlenecks
        }

    async def _analyze_cost(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Analyze cost trends and optimization opportunities."""
        # Get daily cost data
        query = """
            SELECT
                date,
                SUM(total_cost_usd) as daily_cost
            FROM agent_performance
            WHERE date BETWEEN $1 AND $2
            GROUP BY date
            ORDER BY date
        """

        rows = await self.db.fetch(query, start_date, end_date)

        if not rows:
            return {"data_available": False, "message": "No cost data"}

        dates = []
        daily_costs = []

        for row in rows:
            dates.append(row["date"])
            daily_costs.append(float(row["daily_cost"] or 0))

        total_cost = sum(daily_costs)
        avg_daily_cost = statistics.mean(daily_costs) if daily_costs else 0
        max_daily_cost = max(daily_costs) if daily_costs else 0

        # Detect cost spikes
        bottlenecks = []
        if len(daily_costs) > 1:
            avg_cost = statistics.mean(daily_costs)
            std_cost = statistics.stdev(daily_costs) if len(daily_costs) > 1 else 0

            for i, cost in enumerate(daily_costs):
                if cost > avg_cost + 2 * std_cost and std_cost > 0:
                    bottlenecks.append({
                        "date": dates[i].isoformat(),
                        "metric": "cost_spike",
                        "value": cost,
                        "threshold": avg_cost + 2 * std_cost,
                        "severity": BottleneckSeverity.MEDIUM.value
                    })

        # Calculate trend
        trend = await self._detect_cost_trend(dates, daily_costs)

        return {
            "data_available": True,
            "period_days": len(dates),
            "total_cost_usd": total_cost,
            "avg_daily_cost_usd": avg_daily_cost,
            "max_daily_cost_usd": max_daily_cost,
            "daily_costs": list(zip([d.isoformat() for d in dates], daily_costs)),
            "bottlenecks": bottlenecks,
            "trend": trend
        }

    async def _analyze_latency(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Analyze system latency metrics."""
        query = """
            SELECT
                endpoint,
                AVG(latency_ms) as avg_latency,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency,
                COUNT(*) as request_count
            FROM api_usage
            WHERE timestamp::date BETWEEN $1 AND $2
            GROUP BY endpoint
            ORDER BY avg_latency DESC
        """

        rows = await self.db.fetch(query, start_date, end_date)

        if not rows:
            return {"data_available": False, "message": "No latency data"}

        endpoints = []
        bottlenecks = []

        for row in rows:
            endpoint = row["endpoint"]
            avg_latency = row["avg_latency"] or 0
            p95_latency = row["p95_latency"] or 0
            p99_latency = row["p99_latency"] or 0

            endpoints.append({
                "endpoint": endpoint,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "p99_latency_ms": p99_latency,
                "request_count": row["request_count"]
            })

            # Detect latency bottlenecks
            if avg_latency > 3000:  # 3 seconds
                bottlenecks.append({
                    "endpoint": endpoint,
                    "metric": "latency",
                    "value": avg_latency,
                    "threshold": 3000,
                    "severity": BottleneckSeverity.HIGH.value
                })

        return {
            "data_available": True,
            "endpoints_analyzed": len(endpoints),
            "endpoints": endpoints,
            "bottlenecks": bottlenecks
        }

    async def _analyze_error_rate(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Analyze error rates and patterns."""
        query = """
            SELECT
                agent_id,
                COUNT(*) as total_requests,
                SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed_requests
            FROM agent_requests
            WHERE created_at::date BETWEEN $1 AND $2
            GROUP BY agent_id
        """

        rows = await self.db.fetch(query, start_date, end_date)

        if not rows:
            return {"data_available": False, "message": "No error rate data"}

        agent_errors = []
        total_requests = 0
        total_failed = 0
        bottlenecks = []

        for row in rows:
            agent_id = row["agent_id"]
            agent_total = row["total_requests"]
            agent_failed = row["failed_requests"]
            error_rate = agent_failed / max(agent_total, 1)

            agent_errors.append({
                "agent_id": agent_id,
                "total_requests": agent_total,
                "failed_requests": agent_failed,
                "error_rate": error_rate
            })

            total_requests += agent_total
            total_failed += agent_failed

            if error_rate > 0.1:  # 10% error rate
                bottlenecks.append({
                    "agent_id": agent_id,
                    "metric": "error_rate",
                    "value": error_rate,
                    "threshold": 0.1,
                    "severity": BottleneckSeverity.HIGH.value
                })

        overall_error_rate = total_failed / max(total_requests, 1)

        return {
            "data_available": True,
            "total_requests": total_requests,
            "total_failed": total_failed,
            "overall_error_rate": overall_error_rate,
            "agent_error_rates": agent_errors,
            "bottlenecks": bottlenecks
        }

    async def _detect_trend(
        self,
        dates: List[date],
        agents: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect performance trends across agents."""
        if len(dates) < 2:
            return {"direction": TrendDirection.STABLE.value, "confidence": 0.0}

        # Simple trend detection based on success rates
        success_rates = []
        for agent_data in agents.values():
            if agent_data["success_rate"]:
                success_rates.extend(agent_data["success_rate"])

        if len(success_rates) < 2:
            return {"direction": TrendDirection.STABLE.value, "confidence": 0.0}

        # Calculate linear trend
        x = list(range(len(success_rates)))
        y = success_rates

        try:
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        except ImportError:
            # Simple manual calculation if scipy not available
            n = len(x)
            x_mean = sum(x) / n
            y_mean = sum(y) / n

            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0

        if slope > 0.01:
            direction = TrendDirection.IMPROVING.value
        elif slope < -0.01:
            direction = TrendDirection.DEGRADING.value
        else:
            direction = TrendDirection.STABLE.value

        confidence = abs(slope) * 10  # Simple confidence metric

        return {
            "direction": direction,
            "slope": slope,
            "confidence": min(confidence, 1.0)
        }

    async def _detect_cost_trend(
        self,
        dates: List[date],
        daily_costs: List[float]
    ) -> Dict[str, Any]:
        """Detect cost trends."""
        if len(daily_costs) < 2:
            return {"direction": TrendDirection.STABLE.value, "confidence": 0.0}

        # Calculate linear trend
        x = list(range(len(daily_costs)))
        y = daily_costs

        try:
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        except ImportError:
            # Simple manual calculation
            n = len(x)
            x_mean = sum(x) / n
            y_mean = sum(y) / n

            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0

        if slope > 0.1:
            direction = TrendDirection.DEGRADING.value  # Costs increasing
        elif slope < -0.1:
            direction = TrendDirection.IMPROVING.value  # Costs decreasing
        else:
            direction = TrendDirection.STABLE.value

        confidence = abs(slope) / max(y) if max(y) > 0 else 0

        return {
            "direction": direction,
            "slope": slope,
            "confidence": min(confidence, 1.0)
        }

    async def _generate_recommendations(
        self,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []

        # Check for bottlenecks
        bottlenecks = analysis.get("bottlenecks", [])
        for bottleneck in bottlenecks:
            metric = bottleneck.get("metric", "")
            severity = bottleneck.get("severity", "")
            value = bottleneck.get("value", 0)
            threshold = bottleneck.get("threshold", 0)

            if metric == "success_rate":
                recommendations.append({
                    "type": "optimization",
                    "priority": severity,
                    "action": f"Improve success rate for agent {bottleneck.get('agent_name')}",
                    "details": f"Current success rate: {value:.2%}, target: {threshold:.2%}",
                    "estimated_impact": "high"
                })
            elif metric == "latency":
                recommendations.append({
                    "type": "performance",
                    "priority": severity,
                    "action": f"Reduce latency for {bottleneck.get('agent_name', bottleneck.get('endpoint', 'unknown'))}",
                    "details": f"Current latency: {value:.0f}ms, target: {threshold:.0f}ms",
                    "estimated_impact": "medium"
                })
            elif metric == "cost":
                recommendations.append({
                    "type": "cost_optimization",
                    "priority": severity,
                    "action": "Reduce daily cost",
                    "details": f"Current cost: ${value:.2f}, target: ${threshold:.2f}",
                    "estimated_impact": "high"
                })
            elif metric == "cost_concentration":
                recommendations.append({
                    "type": "cost_balancing",
                    "priority": severity,
                    "action": f"Diversify from {bottleneck.get('provider')} provider",
                    "details": f"Provider accounts for {bottleneck.get('percentage', 0):.1%} of total cost",
                    "estimated_impact": "medium"
                })

        # Check overall trends
        for trend in analysis.get("trends", []):
            direction = trend.get("direction", "")
            metric = trend.get("metric", "")

            if direction == TrendDirection.DEGRADING.value:
                recommendations.append({
                    "type": "trend_intervention",
                    "priority": "medium",
                    "action": f"Address degrading trend in {metric}",
                    "details": f"{metric} is trending negatively",
                    "estimated_impact": "medium"
                })

        return recommendations

    async def get_detailed_bottleneck_report(
        self,
        severity: Optional[BottleneckSeverity] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get detailed bottleneck report."""
        # This would query the bottleneck_patterns table
        # For now, return empty
        return {
            "bottlenecks": [],
            "total_count": 0,
            "severity_distribution": {}
        }

    async def get_performance_forecast(
        self,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """Generate performance forecast."""
        # Simple forecasting based on recent trends
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        analysis = await self.analyze_period(start_date, end_date)

        forecast = {
            "forecast_days": days_ahead,
            "predictions": [],
            "confidence": 0.7,  # Placeholder
            "method": "linear_extrapolation"
        }

        # Generate simple predictions
        for metric_type, data in analysis.get("metrics", {}).items():
            if data.get("data_available", False):
                trend = data.get("trend", {})
                slope = trend.get("slope", 0)

                # Simple linear extrapolation
                prediction = data.get("total_cost_usd", 0) + slope * days_ahead
                forecast["predictions"].append({
                    "metric": metric_type,
                    "current_value": data.get("total_cost_usd", 0),
                    "predicted_value": max(prediction, 0),
                    "trend": trend.get("direction", "stable")
                })

        return forecast
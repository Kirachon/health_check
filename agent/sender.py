import time
import logging
from typing import Dict
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource


class MetricsSender:
    """Send metrics to VictoriaMetrics using OpenTelemetry OTLP"""
    
    def __init__(self, config: Dict, device_info: Dict):
        self.config = config
        self.device_info = device_info
        self.logger = logging.getLogger(__name__)

        self._values: Dict[str, float] = {}
        self._attributes = {
            "device_id": self.config.get("device_id", "unknown"),
            "host_name": self.device_info.get("hostname", "unknown"),
            "host_ip": self.device_info.get("ip", "unknown"),
            "os": self.device_info.get("os", "unknown"),
        }
        
        # Configure OpenTelemetry
        self._setup_otel()
        
        # Create gauge instruments for each metric
        self.gauges = {}
    
    def _setup_otel(self):
        """Setup OpenTelemetry SDK"""
        # Create resource with device attributes
        resource = Resource.create({
            "service.name": "health-monitor-agent",
            "device.id": self.config.get("device_id", "unknown"),
            "host.name": self.device_info["hostname"],
            "host.ip": self.device_info["ip"],
            "os.type": self.device_info["os"]
        })
        
        # OTLP exporter to VictoriaMetrics
        otlp_exporter = OTLPMetricExporter(
            endpoint=f"{self.config['server_url']}/opentelemetry/v1/metrics",
            headers={"Authorization": f"Bearer {self.config.get('device_token', '')}"}
        )
        
        # Metric reader with export interval
        reader = PeriodicExportingMetricReader(
            exporter=otlp_exporter,
            export_interval_millis=self.config.get("collection_interval", 30) * 1000
        )
        
        # Meter provider
        provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(provider)
        
        # Get meter
        self.meter = metrics.get_meter("health-monitor")
    
    def _get_or_create_gauge(self, name: str, description: str = "") -> metrics.ObservableGauge:
        """Get or create a gauge for a metric"""
        if name not in self.gauges:
            def callback(options, metric_name=name):
                value = self._values.get(metric_name)
                if value is None:
                    return
                yield metrics.Observation(value, attributes=self._attributes)

            self.gauges[name] = self.meter.create_observable_gauge(
                name=name,
                callbacks=[callback],
                description=description,
                unit=""
            )
        return self.gauges[name]
    
    def send_metrics(self, metrics_data: Dict[str, float]) -> bool:
        """Send metrics to VictoriaMetrics"""
        try:
            for metric_name, value in metrics_data.items():
                self._values[metric_name] = float(value)
                self._get_or_create_gauge(
                    metric_name,
                    description=f"Health monitor metric: {metric_name}",
                )
            
            # Actual OTLP export runs on the periodic reader interval.
            self.logger.info(f"Updated {len(metrics_data)} metrics (next export scheduled)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send metrics: {e}")
            return False
    
    def send_with_retry(self, metrics_data: Dict[str, float]) -> bool:
        """Send metrics with retry logic"""
        max_attempts = self.config.get("retry_attempts", 3)
        retry_delay = self.config.get("retry_delay", 5)
        
        for attempt in range(max_attempts):
            if self.send_metrics(metrics_data):
                return True
            
            if attempt < max_attempts - 1:
                self.logger.warning(f"Retry {attempt + 1}/{max_attempts} in {retry_delay}s...")
                time.sleep(retry_delay)
        
        self.logger.error(f"Failed to send metrics after {max_attempts} attempts")
        return False
    
    def shutdown(self):
        """Gracefully shutdown the exporter"""
        try:
            metrics.get_meter_provider().shutdown()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

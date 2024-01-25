#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-01-23
# ---------------------------------------------------------------------------
"""An agent for collecting, aggregating and sending metrics to a database"""
# ---------------------------------------------------------------------------

import time
import threading

from metrics_agent.aggregator import MetricsAggregatorStats
from metrics_agent.buffer import MetricsBuffer


class MetricsAgent:
    """
    An agent for collecting, aggregating and sending metrics to a database

    Parameters
    ----------
    interval : int
        The time interval (in seconds) between sending metrics to the database
    client : InfluxDatabaseClient
        The client for writing metrics to the database
    aggregator : MetricsAggregator
        The aggregator for aggregating metrics before sending them to the database
    autostart : bool
        Whether to start the aggregator thread automatically upon initialization

    """

    def __init__(self, interval=10, client=None, aggregator=None, autostart=True):
        self._metrics_buffer = MetricsBuffer()
        self._last_sent_time = time.time()
        self._lock = threading.Lock()  # To ensure thread safety

        self.interval = interval
        self.client = client
        self.aggregator = aggregator or MetricsAggregatorStats()

        if autostart:
            self.start_aggregator_thread()

    def add_metric(self, name, value):
        with self._lock:
            self._metrics_buffer.add_metric(name, value)

    def aggregate_and_send(self):
        with self._lock:
            if time.time() - self._last_sent_time >= self.interval:
                if self._metrics_buffer.not_empty():
                    # dump buffer to list of metrics
                    metrics = self._metrics_buffer.dump_buffer()
                    self._last_sent_time = time.time()
                    aggregated_metrics = self.aggregator.aggregate(metrics)
                    self.client.send(aggregated_metrics)

    def start_aggregator_thread(self):
        aggregator_thread = threading.Thread(target=self.run_aggregator, daemon=True)
        aggregator_thread.start()

    def run_aggregator(self):
        while True:
            self.aggregate_and_send()
            time.sleep(1)  # Adjust sleep time as needed

    def stop_aggregator_thread(self):
        self.aggregator_thread.join()

    def clear_metrics_buffer(self):
        with self._lock:
            self._metrics_buffer.clear_buffer()

    def get_metrics_buffer_size(self):
        return self._metrics_buffer.get_buffer_size()

    def run_until_buffer_empty(self):
        while self._metrics_buffer.not_empty():
            time.sleep(self.interval)


def main():
    from metrics_agent.db_client import InfluxDatabaseClient

    client = InfluxDatabaseClient("config/config.toml", local_tz="America/Vancouver")

    # Example usage
    metrics_agent = MetricsAgent(
        interval=1, client=client, aggregator=MetricsAggregatorStats()
    )

    n = 1000000
    # Simulating metric collection
    for _ in range(n):
        metrics_agent.add_metric(name="queries", value=True)

    # Wait for the agent to finish sending all metrics to the database before ending the program
    metrics_agent.run_until_buffer_empty()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

""" A python3 script """

# MIT License
# Copyright (c) HolidayCheck and Contributors
# https://github.com/holidaycheck/gcp-quota-exporter/blob/master/LICENSE
# Github https://github.com/holidaycheck/gcp-quota-exporter

#* File           : exporter.py
#* Description    : A Prometheus exporter for Google Cloud Platform resource quotas.
#*                  Periodically refreshes the quotas for a specific GCP project and
#*                  exposes them as metrics for consumption by Prometheus.
#                   Useful for visibility, tracking, and alerting in case of an impending quota depletion.
#* Version        :  0.2
#* Date           :  May 9, 2020
#*
#* History    :
#*    Date:          Author:       Info:
#*    jan 19, 2019  iwolszewski    Initial import for public (github.com) repository
#*                  romanlevin
#*
#*    May 1, 2010   my10c          Adding MODE, if set to debug then it will just execute a
#*                                 long sleep, default to production. PORT if not set then defult to 8000.
#*    May 10, 2020  my10c          Ignore updates of a metrics if the usage is 0.
#*                                 Adding the labels 'service' and 'type_quota' to
#*                                 make search in Prometheus and Grafana easier
#*                                 METRICS_MODE is set to ALL then show all metric, oherwise only the one with usage > 0

import os
import traceback
import typing
import sys
import time

import apscheduler.schedulers.blocking
import googleapiclient.discovery
import prometheus_client

__progname__ = os.path.basename(__file__)
__copyright__ = 'Copyright 2019 - ' + time.strftime('%Y') + ' © HolidayCheck and Contributors'
__license__ = 'MIT, https://github.com/holidaycheck/gcp-quota-exporter/blob/master/LICENSE'
__version__ = '0.2'
__info__ = '%s\nVersion %s\nCopyrigh %s\nLicense %s\n' % (__progname__, __version__, __copyright__, __license__)
__description__ = 'A Prometheus exporter for Google Cloud Platform resource quotas.\n' +\
 'Periodically refreshes the quotas for a specific GCP project and\n' +\
 'exposes them as metrics for consumption by Prometheus.\n' +\
 'Useful for visibility, tracking, and alerting in case of an impending quota depletion.'
__help__ = 'No argument required, {} uses the following enviroment variables:\n'.format(__progname__) +\
 'MODE                : if set to debug then execute a long sleep, default to production\n' +\
 'PORT                : the port to accept requests, default to 8000\n' +\
 'QE_PROJECT_ID       : required, the GCP project id\n' +\
 'QE_REFRESH_INTERVAL : refresh rate, default to 60 seconds\n' +\
 'METRICS_MODE        : if set to ALL then generate all metrics, otherwise only if usage is not 0, default NOTZERO\n' +\
 'GOOGLE_APPLICATION_CREDENTIALS : required, the location of the GCP credential file'


TIMESTAMP_METRIC_NAME = "gcloud_exporter_last_update_unixtime"


def create_metric_name() -> str:
    """
    Create the metric name, make it easy selectable
    """
    ##return f'gcloud_{resource.lower()}_quota_{kind}'
    return f'gcloud_quota'


def usage_ratio(usage: float, limit: float) -> float:
    """
    Calculate the usage ratio
    """
    return 0.0 if limit <= 0 else usage/limit


class QuotaUpdater:
    """
    Container object for the GCP API client and Prometheus metrics.

    """
    def __init__(self, project_id: str, compute_client: googleapiclient.discovery.Resource, http_port, metrics_mode):
        self.project_id = project_id
        self.compute_client = compute_client
        self.http_port = int(http_port)
        self.metrics: typing.Dict[str, prometheus_client.core.Gauge] = {}
        self.registry = prometheus_client.CollectorRegistry(auto_describe=True)
        self.metrics_mode = metrics_mode

    def run(self):
        """
        Updates all the metrics.
        """
        try:
            self.update_regional_quotas()
            self.update_global_quotas()
            self.update_timestamp()
        except Exception:
            print("Exception occurred while updating quotas data:")
            print(traceback.format_exc())

    def update_timestamp(self):
        """
        Update the timestamp when the metric was updated
        """
        if TIMESTAMP_METRIC_NAME not in self.metrics:
            self.metrics[TIMESTAMP_METRIC_NAME] = prometheus_client.Gauge(
                TIMESTAMP_METRIC_NAME,
                "Date of last successful quotas data update as unix timestamp/epoch",
                registry=self.registry)
        self.metrics[TIMESTAMP_METRIC_NAME].set_to_current_time()

    def update_regional_quotas(self):
        """
        Update that are regional bases
        """
        api_result = self.compute_client.regions().list(project=self.project_id, fields='items(name,quotas)').execute()
        for region in api_result['items']:
            if self.metrics_mode == 'ALL':
                # this will update all
                self.publish_region_quotas(region)
            else:
                # create the dict with metrics where usage is > 0
                region_dict = {}
                quota_list = []
                region_dict['name'] = region['name']
                for metric in region['quotas']:
                    if metric['usage'] > 0:
                        quota_list.append(metric)
                region_dict['quotas'] = quota_list
                self.publish_region_quotas(region_dict)

    def update_global_quotas(self):
        """
        Update that are global
        """
        api_result = self.compute_client.projects().get(
            project=self.project_id, fields='quotas').execute()
        if self.metrics_mode == 'ALL':
            # this will update all
            self.publish_global_quotas(api_result['quotas'])
        else:
            # create the list with metrics where usage is > 0
            quota_list = []
            for metric in api_result['quotas']:
                if metric['usage'] > 0:
                    quota_list.append(metric)
            self.publish_global_quotas(quota_list)

    def publish_region_quotas(self, region: dict):
        """
            region = {
                'name': 'asia-east1',
                'quotas': [
                    {'limit': 72.0, 'metric': 'CPUS', 'usage': 0.0},
                    ...
                ]
            }
        """
        for quota in region['quotas']:
            for kind in ('limit', 'usage'):
                self.publish_value(quota[kind], quota['metric'], kind, self.project_id, region['name'])
            self.publish_value(
                usage_ratio(quota['usage'], quota['limit']), quota['metric'],
                'ratio', self.project_id, region['name'])

    def publish_global_quotas(self, quotas: list):
        """
        quotas = [
            {'limit': 5000.0, 'metric': 'SNAPSHOTS', 'usage': 527.0},
            {'limit': 15.0, 'metric': 'NETWORKS', 'usage': 2.0},
            ...
        ]
        """
        for quota in quotas:
            for kind in ('limit', 'usage'):
                self.publish_value(quota[kind], quota['metric'], kind, self.project_id)
            self.publish_value(
                usage_ratio(quota['usage'], quota['limit']), quota['metric'], 'ratio', self.project_id)

    def publish_value(self, value: float, resource: str, kind: str, project_id: str, region: str = 'global'):
        """
        Publish the current quota of the givem metric
        """
        metric_name = create_metric_name()

        if metric_name not in self.metrics:
            # set lables to project_id, region, quota_service and quota_type
            # this make seatch and regex for alerting much easier
            self.metrics[metric_name] = prometheus_client.Gauge(
                metric_name, f'Google Cloud quota for {resource} resource',
                ['project_id', 'region', 'quota_service', 'quota_type'], registry=self.registry
            )

        self.metrics[metric_name].labels(project_id=project_id, region=region,\
            quota_service=resource.lower(), quota_type=kind.lower()).set(float(value))

    def serve(self):
        """
        Starts a non-blocking HTTP server serving the prometheus metrics
        """
        prometheus_client.start_http_server(self.http_port, registry=self.registry)


def main():
    """
    The main  function
    """
    if len(sys.argv) > 1:
        if sys.argv[1] == 'version':
            print('{}'.format(__info__))
            sys.exit(0)
        if sys.argv[1] == 'info':
            print('{}\n{}'.format(__info__, __description__))
            sys.exit(0)
        # everything else show the help info
        print('{}\n{}'.format(__info__, __help__))
        sys.exit(0)

    try:
        mode = os.environ['MODE']
    except KeyError:
        mode = 'production'

    try:
        metrics_mode = os.environ['METRICS_MODE']
    except KeyError:
        metrics_mode = 'NOTZERO'

    try:
        http_server_port = os.environ['PORT']
    except KeyError:
        http_server_port = 8000

    print('Running in {} mode'.format(mode))
    if mode == "debug":
        time.sleep(500000)

    try:
        gcloud_project_id = os.environ['QE_PROJECT_ID']
    except KeyError:
        print('{}'.format(__info__))
        print('QE_PROJECT_ID must be defined')
        sys.exit(1)

    try:
        refresh_interval_seconds = int(os.getenv('QE_REFRESH_INTERVAL', '60'))
    except TypeError:
        print('{}'.format(__info__))
        print('QE_REFRESH_INTERVAL must be a number')
        sys.exit(1)

    print('Initialization..')
    compute = googleapiclient.discovery.build('compute', 'v1')
    quota_updater = QuotaUpdater(gcloud_project_id, compute, http_server_port, metrics_mode)

    scheduler = apscheduler.schedulers.blocking.BlockingScheduler()
    scheduler.add_job(quota_updater.run, trigger='interval', seconds=refresh_interval_seconds, timezone='UTC')

    print('Verifying permissions..')
    quota_updater.run()

    quota_updater.serve()

    print('Starting scheduler')
    scheduler.start()


if __name__ == "__main__":
    main()

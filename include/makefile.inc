
NAMESPACE=gcp-quota-exporter-test
PORT=8000
MODE=debug
IMAGE=my10c/gcp-quota-exporter
VERSION=0.1
TAG=$(IMAGE):$(VERSION)
DOCKERFILE=Dockerfile
PROJECT=
GCR_RPOJECT=

GCR_US=us.gcr.io/$(GCR_RPOJECT)/$(TAG)
GCR_ASIA=asia.gcr.io/$(GCR_RPOJECT)/$(TAG)
GCR_EU=eu.gcr.io/$(GCR_RPOJECT)/$(TAG)

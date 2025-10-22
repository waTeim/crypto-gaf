MAKE_ENV ?= make.env
ifneq (,$(wildcard $(MAKE_ENV)))
include $(MAKE_ENV)
export
endif

REGISTRY ?= localhost
IMAGE_NAME ?= crypto-gaf
TAG ?= latest
PLATFORM ?= linux/amd64
.PHONY: build push build-collect build-calculate build-api push-collect push-calculate push-api

build: build-collect build-calculate build-api

push: push-collect push-calculate push-api

build-collect:
	@echo "Building collect"
	docker build --platform $(PLATFORM) --pull --rm -t $(REGISTRY)/$(IMAGE_NAME)-collect:$(TAG) collect

build-calculate:
	@echo "Building calculate"
	docker build --platform $(PLATFORM) --pull --rm -t $(REGISTRY)/$(IMAGE_NAME)-calculate:$(TAG) calculate

build-api:
	@echo "Building api"
	docker build --platform $(PLATFORM) --pull --rm -t $(REGISTRY)/$(IMAGE_NAME)-api:$(TAG) api

push-collect:
	@echo "Pushing collect"
	docker push $(REGISTRY)/$(IMAGE_NAME)-collect:$(TAG)

push-calculate:
	@echo "Pushing calculate"
	docker push $(REGISTRY)/$(IMAGE_NAME)-calculate:$(TAG)

push-api:
	@echo "Pushing api"
	docker push $(REGISTRY)/$(IMAGE_NAME)-api:$(TAG)

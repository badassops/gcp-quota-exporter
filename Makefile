
include include/makefile.inc

all:
	@echo "\n\t *** valid options are: build run start stop status shell push list ***"
	@echo "\t *** use these options with caution: clean clean-all delete-images ***\n"

build:
	@echo "\t *** build image using file: $(DOCKERFILE) ***\n"
	@docker build --network=host --no-cache --pull -f $(DOCKERFILE) -t $(TAG) \
			--build-arg "PORT=$(PORT)" \
			.
	@echo "-----------------"
	@docker images
	@echo "-----------------"

run:
	@echo "\t *** runing image $(TAG) with namespace $(NAMESPACE) ***\n"
	@echo "-----------------"
	@docker run --network=host --detach \
		--env "MODE=debug" \
		--env "PORT=$(PORT)" \
		--env "QE_PROJECT_ID=$(PROJECT)" \
		--name $(NAMESPACE) $(TAG)
	@echo "-----------------"
	@docker ps -a
	@echo "-----------------"

start:
	@echo "\t *** starting the container $(TAG) ***\n"
	@$(eval DOCKERID=$(shell sh -c "docker ps -a | grep '$(TAG)'" | awk '{print $$1;}'))
	@echo "-----------------"
	@docker start $(DOCKERID)
	@echo "-----------------"
	@docker ps -a
	@echo "-----------------"

stop:
	@echo "\t *** stoping the container $(TAG) ***\n"
	@$(eval DOCKERID=$(shell sh -c "docker ps -a | grep '$(TAG)'" | awk '{print $$1;}'))
	@echo "-----------------"
	@docker stop $(DOCKERID)
	@echo "-----------------"
	@docker ps -a
	@echo "-----------------"

status:
	@echo "\t *** status of the container $(TAG) ***\n"
	@echo "-----------------"
	@docker ps -a
	@echo "-----------------"

shell:
	@echo "\t *** shelling into the container $(TAG) ***\n"
	@$(eval DOCKERID=$(shell sh -c "docker ps -a | grep '$(TAG)'" | awk '{print $$1;}'))
	@docker exec -u 0 -ti $(DOCKERID) /bin/bash

push:
	@echo "\t--- adding GCR tag --------------"
	@docker tag $(TAG) $(GCR_US)
	@docker tag $(TAG) $(GCR_EU)
	@docker tag $(TAG) $(GCR_ASIA)
	@docker images | grep $(IMAGE)
	@echo "\n\t--- pushing to: GCR: US - EU - ASIA --------------"
	docker push $(GCR_US)
	docker push $(GCR_EU)
	docker push $(GCR_ASIA)

list:
	@for repo in $(GCR_US) $(GCR_EU) $(GCR_ASIA) ; do \
		echo "\n\t *** repo $$repo ***" ;\
		gcloud container images list-tags $$repo/$(GCR_RPOJECT)/$(IMAGE) ;\
	done;
	@echo "-----------------"

clean:	clean-container clean-images
	@echo "\t *** cleaning all containers and images for $(TAG) *** \n"
	@echo "-----------------"
	@docker ps -a
	@echo "-----------------"
	docker images -a
	@echo "-----------------"

clean-container:
	@$(eval DOCKERID=$(shell sh -c "docker ps -a | grep '$(IMAGE)'" | awk '{print $$1;}'))
	@if [ ! -z $(DOCKERID) ] ; then \
		docker rm -f $(DOCKERID) >/dev/null 2>&1 ;\
	fi

clean-images:
	@$(eval DOCKERID=$(shell sh -c "docker images -a | grep '$(IMAGE)'" | awk '{print $$3;}'))
	@if [ ! -z $(DOCKERID) ] ; then \
		docker rmi -f $(DOCKERID) >/dev/null 2>&1 ;\
	fi

delete-images:
	@echo "\t *** cleaning old images *** \n"
	@echo -n "\t *** DANGER WILL ROBINSON, PRESS ENTER Y IF YOU ARE 100%% SURE: "
	@read Inkey ; if [ "$$Inkey" = "Y" ] ; then \
			bin/delete_images $(GCR_RPOJECT) $(IMAGE) $(VERSION) ;\
		else \
			echo "\t ** No GCR image will be deleted **" ;\
	fi

logs:
	@echo "\t *** logs from container *** \n"
	@$(eval DOCKERID=$(shell sh -c "docker ps -a | grep '$(TAG)'" | awk '{print $$1;}'))
	@if [ ! -z $(DOCKERID) ] ; then \
		@docker logs $(LOG_OPTION) $(DOCKERID) \
	fi

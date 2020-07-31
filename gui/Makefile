ACCOUNT=klotio
IMAGE=app
VERSION?=0.1

.PHONY: cross build shell push install update remove reset

cross:
	docker run --rm --privileged multiarch/qemu-user-static:register --reset

build:
	docker build . -t $(ACCOUNT)/$(IMAGE):$(VERSION)

shell:
	-docker run -it --rm $(ACCOUNT)/$(IMAGE):$(VERSION) sh

push:
	docker push $(ACCOUNT)/$(IMAGE):$(VERSION)

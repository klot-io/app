IMAGE=klotio-app
VERSION=0.1
ACCOUNT=klotio
NETWORK=klot.io
VOLUMES=-v ${PWD}/lib:/opt/klot-io/lib \
		-v ${PWD}/test:/opt/klot-io/test \
		-v ${PWD}/setup.py:/opt/klot-io/setup.py
ENVIRONMENT=-e MYSQL_HOST=mysql-klotio \
			-e MYSQL_PORT=3306 \
			-e PYTHONUNBUFFERED=1

.PHONY: build shell test tag

build:
	docker build . -t $(ACCOUNT)/$(IMAGE):$(VERSION)

network:
	-docker network create $(NETWORK)

shell: network
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh

test: network
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "coverage run -m unittest discover -v test && coverage report -m --include 'klotio/*.py'"

setup: network
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "python setup.py install"

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags
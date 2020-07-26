IMAGE=klotio-app
VERSION=0.2
ACCOUNT=klotio
NETWORK=app.klot.io
MYSQL=klotio/mysql:0.3
MYSQL_HOST=$(IMAGE)-mysql
VOLUMES=-v ${PWD}/lib:/opt/klot-io/lib \
		-v ${PWD}/test:/opt/klot-io/test \
		-v ${PWD}/setup.py:/opt/klot-io/setup.py \
		-v ${PWD}/mysql.sh:/opt/klot-io/mysql.sh
ENVIRONMENT=-e MYSQL_HOST=$(MYSQL_HOST) \
			-e MYSQL_PORT=3306 \
			-e PYTHONUNBUFFERED=1

.PHONY: build mysql shell test setup tag untag

build:
	docker build . -t $(ACCOUNT)/$(IMAGE):$(VERSION)

network:
	-docker network create $(NETWORK)

mysql: network
	-docker rm --force $(MYSQL_HOST)
	docker run -d --network=$(NETWORK) -h $(MYSQL_HOST) --name=$(MYSQL_HOST) -e MYSQL_ALLOW_EMPTY_PASSWORD='yes' $(MYSQL)
	docker run -it --rm --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "./mysql.sh"

shell: mysql
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh
	docker rm --force $(MYSQL_HOST)

test: mysql
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "coverage run -m unittest discover -v test && coverage report -m --include 'klotio/*.py'"
	docker rm --force $(MYSQL_HOST)

setup:
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) klotio/python:0.1 sh -c "cd /opt/klot-io/ && python setup.py install"

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags

untag:
	-git tag -d "v$(VERSION)"
	git push origin ":refs/tags/v$(VERSION)"
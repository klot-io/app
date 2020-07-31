IMAGE=app
ACCOUNT=klotio
NETWORK=app.klot.io
MYSQL_IMAGE=klotio/mysql:0.3
MYSQL_HOST=$(ACCOUNT)-$(IMAGE)-mysql
DEBUG_PORT=5678
VOLUMES=-v ${PWD}/lib:/opt/klot-io/lib \
		-v ${PWD}/test:/opt/klot-io/test \
		-v ${PWD}/mysql.sh:/opt/klot-io/mysql.sh
ENVIRONMENT=-e MYSQL_HOST=$(MYSQL_HOST) \
			-e MYSQL_PORT=3306 \
			-e PYTHONDONTWRITEBYTECODE=1 \
			-e PYTHONUNBUFFERED=1

.PHONY: build network mysql shell debug test

build:
	docker build . -t $(ACCOUNT)/$(IMAGE)

network:
	-docker network create $(NETWORK)

mysql: network
	-docker rm --force $(MYSQL_HOST)
	docker run -d --network=$(NETWORK) -h $(MYSQL_HOST) --name=$(MYSQL_HOST) -e MYSQL_ALLOW_EMPTY_PASSWORD='yes' $(MYSQL_IMAGE)
	docker run -it --rm --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE) sh -c "./mysql.sh"

shell: mysql
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE) sh
	docker rm --force $(MYSQL_HOST)

debug: mysql
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) -p 127.0.0.1:$(DEBUG_PORT):5678 $(ACCOUNT)/$(IMAGE) sh -c "python -m ptvsd --host 0.0.0.0 --port 5678 --wait -m unittest discover -v test"
	docker rm --force $(MYSQL_HOST)

test: mysql
	docker run -it --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE) sh -c "coverage run -m unittest discover -v test && coverage report -m --include 'lib/klotio/*.py'"
	docker rm --force $(MYSQL_HOST)

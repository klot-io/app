VERSION=0.3
IMAGE=arm32v7/python:3.8.5-alpine3.12
VOLUMES=-v ${PWD}/api:/opt/klot-io/api \
		-v ${PWD}/setup.py:/opt/klot-io/setup.py

.PHONY: setup tag untag

setup:
	docker run -it $(VOLUMES) $(IMAGE) sh -c "cd /opt/klot-io/ && python setup.py install"

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags

untag:
	-git tag -d "v$(VERSION)"
	git push origin ":refs/tags/v$(VERSION)"
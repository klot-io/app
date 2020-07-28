VERSION=0.3
VOLUMES=-v ${PWD}/api:/opt/klot-io/api \
		-v ${PWD}/setup.py:/opt/klot-io/setup.py

.PHONY: setup tag untag

setup:
	docker run -it $(VOLUMES) klotio/python:0.1 sh -c "cd /opt/klot-io/ && python setup.py install"

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags

untag:
	-git tag -d "v$(VERSION)"
	git push origin ":refs/tags/v$(VERSION)"
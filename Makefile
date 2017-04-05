VERSION = 2.2.0

man:
	cd docs && make man
	cp docs/build/man/* data/
	@echo "Now commit the updated man pages"

sdist:
	python setup.py sdist

sign:
	gpg --no-version --detach-sign --armor --local-user 0x702287F4 dist/ooniprobe-${VERSION}.tar.gz

upload:
	twine upload -r pypi dist/ooniprobe-${VERSION}.tar.gz  dist/ooniprobe-${VERSION}.tar.gz.asc

docker-build:
	docker build -t ooniprobe .

docker-run-d: docker-build
	docker run -d -p 80:8842 ooniprobe

docker-run: docker-build
	docker run -p 80:8842 ooniprobe

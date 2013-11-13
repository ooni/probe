# This file will fetch a set of inputs that are of use to ooni-probe
all: whatheaders lists

lists:
	curl -O https://ooni.torproject.org/inputs/input-pack.tar.gz
	tar xzf input-pack.tar.gz
	rm input-pack.tar.gz

whatheaders:
	wget http://s3.amazonaws.com/data.whatheaders.com/whatheaders-latest.xml.zip
	unzip whatheaders-latest.xml.zip
	mv whatheaders*.xml whatheaders.xml
	rm whatheaders-latest.xml.zip

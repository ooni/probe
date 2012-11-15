# This file will fetch a set of inputs that are of use to ooni-probe
all: whatheaders lists

lists:
	git clone https://github.com/hellais/ooni-inputs.git ooni-inputs

whatheaders:
	wget http://s3.amazonaws.com/data.whatheaders.com/whatheaders-latest.xml.zip
	unzip whatheaders-latest.xml.zip
	mv whatheaders*.xml whatheaders.xml
	rm whatheaders-latest.xml.zip

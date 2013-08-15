geoip:
	wget -N http://www.maxmind.com/download/geoip/database/asnum/GeoIPASNum.dat.gz
	gunzip -f GeoIPASNum.dat.gz
	wget -N http://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz
	gunzip -f GeoIP.dat.gz
	wget -N http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz
	gunzip -f GeoLiteCity.dat.gz
clean:
	rm -f *.dat


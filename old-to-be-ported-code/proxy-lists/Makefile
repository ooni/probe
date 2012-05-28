default:
	wget http://www.wikimedia.org/trusted-xff.html --output-document=trusted-xff.html

iplist:
	./parse-trusted-xff.sh
	cat italy-dns.txt|cut -d\  -f2 > italy-dns-ips.txt
	cat italy-http-block-pages.txt|cut -d\  -f2 > italy-http-ips.txt
	cat italy-dns-ips.txt italy-http-block-pages.txt >> ips.txt

clean:
	rm italy-dns-ips.txt italy-http-ips.txt ips.txt

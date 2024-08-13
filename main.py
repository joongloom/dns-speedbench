import dns.resolver
import time

DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "77.88.8.8", "9.9.9.9"]
TEST_DOMAIN = "google.com"

def check_dns(ip):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [ip]
    resolver.timeout = 2.0
    resolver.lifetime = 2.0
    
    try:
        start = time.perf_counter()
        resolver.resolve(TEST_DOMAIN, "A")
        end = time.perf_counter()
        return (end - start) * 1000
    except:
        return None

def main():
    print(f"Testing {len(DNS_SERVERS)} servers...")
    
    for ip in DNS_SERVERS:
        latency = check_dns(ip)
        if latency is not None:
            print(f"{ip:<15} | {latency:.2f} ms")
        else:
            print(f"{ip:<15} | Failed")

if __name__ == "__main__":
    main()
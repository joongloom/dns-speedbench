import dns.resolver
import time
import csv
import subprocess
import re
import platform
import os

DNS_SERVERS_FILE = "dns_servers.csv"
TEST_DOMAIN = "google.com"

def get_system_dns():
    ips = []
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["ipconfig", "/all"], text=True, errors="ignore")
            found = re.findall(r":\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", output)
            ips = [ip for ip in found if not ip.startswith("127.") and not ip.startswith("255.")]
        else:
            if os.path.exists("/etc/resolv.conf"):
                with open("/etc/resolv.conf", "r") as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            ips.append(line.split()[1])
    except:
        pass
    return list(dict.fromkeys(ips))

def load_from_csv(filename):
    servers = []
    if not os.path.exists(filename):
        return servers
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and not row[0].startswith("#"):
                    for item in row:
                        item = item.strip()
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", item):
                            servers.append(item)
    except:
        pass
    return list(dict.fromkeys(servers))

def test_dns(ip):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [ip]
    resolver.timeout = 2.0
    resolver.lifetime = 2.0
    try:
        start = time.perf_counter()
        resolver.resolve(TEST_DOMAIN, "A")
        return (time.perf_counter() - start) * 1000
    except:
        return None

def main():
    system_ips = get_system_dns()
    csv_ips = load_from_csv(DNS_SERVERS_FILE)
    all_servers = list(dict.fromkeys(system_ips + csv_ips))
    
    print(f"Loaded {len(all_servers)} servers.")
    
    results = []
    for ip in all_servers:
        print(f"Testing {ip}...", end="\r")
        latency = test_dns(ip)
        if latency:
            results.append((ip, latency))
    
    print("\nTop 10 results:")
    for ip, t in sorted(results, key=lambda x: x[1])[:10]:
        print(f"{ip:<15} | {t:.2f} ms")

if __name__ == "__main__":
    main()
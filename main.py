import dns.resolver
import time
import csv
import subprocess
import re
import platform
import os
import concurrent.futures
from typing import List, Dict, Optional, Tuple

class DNSBenchmark:
    def __init__(self, filename: str = "dns_servers.csv"):
        self.filename = filename
        self.test_domain = "google.com"
        self.timeout = 2.0
        self.results: Dict[str, float] = {}

    def get_system_dns(self) -> List[str]:
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
                            if line.strip().startswith("nameserver"):
                                ips.append(line.split()[1])
        except:
            pass
        return list(dict.fromkeys(ips))

    def load_csv(self) -> List[str]:
        servers = []
        if not os.path.exists(self.filename):
            return servers
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
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

    def test_single_server(self, ip: str) -> Tuple[str, Optional[float]]:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [ip]
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout
        try:
            start = time.perf_counter()
            resolver.resolve(self.test_domain, "A")
            return ip, (time.perf_counter() - start) * 1000
        except:
            return ip, None

    def run(self):
        system_ips = self.get_system_dns()
        csv_ips = self.load_csv()
        all_servers = list(dict.fromkeys(system_ips + csv_ips))

        print(f"Starting benchmark for {len(all_servers)} servers...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {executor.submit(self.test_single_server, ip): ip for ip in all_servers}
            for future in concurrent.futures.as_completed(future_to_ip):
                ip, latency = future.result()
                if latency:
                    self.results[ip] = latency
                    print(f"  [+] {ip:<15} - {latency:.2f} ms")

        print("\n--- Top Results ---")
        sorted_res = sorted(self.results.items(), key=lambda x: x[1])
        for i, (ip, t) in enumerate(sorted_res[:10], 1):
            print(f"{i}. {ip:<15} | {t:.2f} ms")

if __name__ == "__main__":
    bench = DNSBenchmark()
    bench.run()
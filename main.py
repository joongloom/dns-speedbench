import argparse
import concurrent.futures
import csv
import os
import platform
import random
import re
import statistics
import string
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

import dns.resolver

class DNSBenchmark:
    def __init__(self, csv_file: str, test_domain: str = "google.com"):
        self.csv_file = csv_file
        self.test_domain = test_domain
        self.timeout = 2.0
        self.queries = 3
        self.max_workers = 20
        self.results: Dict[str, float] = {}
        self.metadata: Dict[str, Dict] = {}
        self.system_dns: List[str] = []

    def _get_system_dns(self) -> List[str]:
        ips = []
        try:
            if platform.system() == "Windows":
                out = subprocess.check_output(["ipconfig", "/all"], text=True, errors="ignore")
                ips = re.findall(r":\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", out)
                ips = [ip for ip in ips if not ip.startswith(("127.", "255.", "169.254"))]
            else:
                if os.path.exists("/etc/resolv.conf"):
                    with open("/etc/resolv.conf", "r") as f:
                        for line in f:
                            if line.startswith("nameserver"):
                                ips.append(line.split()[1])
        except:
            pass
        return list(dict.fromkeys(ips))

    def _load_servers(self):
        self.system_dns = self._get_system_dns()
        to_test = set(self.system_dns)
        
        for ip in self.system_dns:
            self.metadata[ip] = {"provider": "Системный DNS", "location": "Локальный"}

        if os.path.exists(self.csv_file):
            try:
                with open(self.csv_file, "r", encoding="utf-8") as f:
                    for row in csv.reader(f):
                        if not row or row[0].startswith("#") or len(row) < 3:
                            continue
                        provider, country, ip1 = map(str.strip, row[:3])
                        ip2 = row[3].strip() if len(row) > 3 else None
                        
                        for ip in filter(None, [ip1, ip2]):
                            to_test.add(ip)
                            self.metadata[ip] = {"provider": provider, "location": country}
            except:
                pass
        
        return list(to_test)

    def _test_server(self, ip: str) -> Tuple[str, Optional[float]]:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [ip]
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout
        
        latencies = []
        try:
            for _ in range(self.queries):
                salt = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                target = f"{salt}.{self.test_domain}"
                
                start = time.perf_counter()
                try:
                    resolver.resolve(target, "A")
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    pass
                latencies.append((time.perf_counter() - start) * 1000)
            
            return ip, statistics.median(latencies)
        except:
            return ip, None

    def run(self):
        servers = self._load_servers()
        if not servers:
            print("[!] Нет серверов для проверки.")
            return

        print(f"[*] Тестируем {len(servers)} серверов (по {self.queries} запроса, обход кеша включен)...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._test_server, ip): ip for ip in servers}
            
            done = 0
            for future in concurrent.futures.as_completed(futures):
                ip, latency = future.result()
                if latency:
                    self.results[ip] = latency
                done += 1
                sys.stdout.write(f"\rПрогресс: {done}/{len(servers)}")
                sys.stdout.flush()

        print("\n" + "="*85)
        print(f"{'№':<3} {'IP Адрес':<18} {'Провайдер':<22} {'Регион':<15} {'Задержка':<10}")
        print("-" * 85)

        sorted_res = sorted(self.results.items(), key=lambda x: x[1])
        for i, (ip, lat) in enumerate(sorted_res[:15], 1):
            meta = self.metadata.get(ip, {})
            marker = "*" if ip in self.system_dns else " "
            print(f"{marker}{i:<2} {ip:<18} {meta.get('provider', 'N/A'):<22} "
                  f"{meta.get('location', 'N/A'):<15} {lat:>7.2f} мс")
        
        print("-" * 85)
        print("* — текущий DNS вашей системы.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", default="dns_servers.csv")
    parser.add_argument("-d", "--domain", default="google.com")
    args = parser.parse_args()

    try:
        app = DNSBenchmark(args.file, args.domain)
        app.run()
    except KeyboardInterrupt:
        print("\n[!] Прервано пользователем.")
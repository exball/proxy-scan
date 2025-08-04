#!/usr/bin/env python3
"""
Proxy Checker Script
Memeriksa respon proxy:port dari file yang berisi daftar proxy
Mendukung format: IP,PORT atau IP,PORT,COUNTRY,ISP
"""

import requests
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys
import os

class ProxyChecker:
    def __init__(self):
        self.working_proxies = []
        self.not_working_proxies = []
        self.lock = threading.Lock()
        self.progress_count = 0
        self.total_proxies = 0
        
    def detect_file_format(self, file_path):
        """Deteksi format file proxy"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                
            if not first_line:
                return None
                
            parts = first_line.split(',')
            
            if len(parts) >= 2:
                # Cek apakah part kedua adalah angka (port)
                try:
                    int(parts[1])
                    if len(parts) == 2:
                        return "ip_port"  # Format: IP,PORT
                    elif len(parts) >= 4:
                        return "ip_port_info"  # Format: IP,PORT,COUNTRY,ISP
                    else:
                        return "ip_port"  # Default ke format sederhana
                except ValueError:
                    return None
            
            return None
            
        except Exception as e:
            print(f"Error detecting file format: {e}")
            return None
    
    def load_proxies_from_file(self, file_path):
        """Load proxy list dari file"""
        try:
            format_type = self.detect_file_format(file_path)
            
            if not format_type:
                print(f"❌ Format file tidak dikenali: {file_path}")
                return []
            
            proxies = []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        parts = line.split(',')
                        
                        if len(parts) >= 2:
                            ip = parts[0].strip()
                            port = parts[1].strip()
                            
                            # Validasi IP dan port
                            if ip and port.isdigit():
                                proxy_string = f"{ip}:{port}"
                                
                                # Tambahkan info tambahan jika ada
                                extra_info = ""
                                if format_type == "ip_port_info" and len(parts) >= 4:
                                    country = parts[2].strip()
                                    isp = parts[3].strip()
                                    extra_info = f" ({country}, {isp})"
                                
                                proxies.append({
                                    'proxy': proxy_string,
                                    'extra_info': extra_info,
                                    'line_num': line_num
                                })
                            else:
                                print(f"⚠️  Line {line_num}: Invalid format - {line}")
                        else:
                            print(f"⚠️  Line {line_num}: Insufficient data - {line}")
                            
                    except Exception as e:
                        print(f"⚠️  Line {line_num}: Error parsing - {e}")
            
            # Remove duplicates
            unique_proxies = []
            seen = set()
            
            for proxy_data in proxies:
                if proxy_data['proxy'] not in seen:
                    unique_proxies.append(proxy_data)
                    seen.add(proxy_data['proxy'])
            
            duplicates_removed = len(proxies) - len(unique_proxies)
            
            print(f"📊 Loaded from {Path(file_path).name}:")
            print(f"   📋 Total lines processed: {len(proxies)}")
            print(f"   🎯 Unique proxies: {len(unique_proxies)}")
            if duplicates_removed > 0:
                print(f"   🗑️  Duplicates removed: {duplicates_removed}")
            print(f"   📝 Format detected: {format_type}")
            
            return unique_proxies
            
        except Exception as e:
            print(f"❌ Error loading file {file_path}: {e}")
            return []
    
    def test_single_proxy(self, proxy_data, timeout=10):
        """Test single proxy"""
        proxy_string = proxy_data['proxy']
        
        try:
            # Setup proxy
            proxies = {
                'http': f'http://{proxy_string}',
                'https': f'http://{proxy_string}'
            }
            
            # Test request
            start_time = time.time()
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            response_time = time.time() - start_time
            
            # Analyze response
            is_working = False
            status_reason = f"{response.status_code} - Other response"
            
            response_text = response.text.lower()
            
            # Check for cloudflare responses (working criteria)
            if response.status_code == 403 and 'cloudflare' in response_text:
                is_working = True
                status_reason = "403 Forbidden cloudflare"
            elif (response.status_code == 400 and 
                  'https port' in response_text and 
                  'cloudflare' in response_text):
                is_working = True
                status_reason = "400 Bad Request HTTPS port cloudflare"
            
            result = {
                'proxy': proxy_string,
                'extra_info': proxy_data['extra_info'],
                'is_working': is_working,
                'reason': status_reason,
                'response_time': response_time,
                'line_num': proxy_data['line_num']
            }
            
            return result
            
        except requests.exceptions.ProxyError:
            return {
                'proxy': proxy_string,
                'extra_info': proxy_data['extra_info'],
                'is_working': False,
                'reason': 'Proxy connection failed',
                'response_time': None,
                'line_num': proxy_data['line_num']
            }
        except requests.exceptions.Timeout:
            return {
                'proxy': proxy_string,
                'extra_info': proxy_data['extra_info'],
                'is_working': False,
                'reason': 'Request timeout',
                'response_time': None,
                'line_num': proxy_data['line_num']
            }
        except Exception as e:
            return {
                'proxy': proxy_string,
                'extra_info': proxy_data['extra_info'],
                'is_working': False,
                'reason': f'Connection error: {str(e)[:50]}',
                'response_time': None,
                'line_num': proxy_data['line_num']
            }
    
    def update_progress(self, result):
        """Update progress counter"""
        with self.lock:
            self.progress_count += 1
            
            if result['is_working']:
                self.working_proxies.append(result)
                status = "✅"
                reason = result['reason']
                if result['response_time']:
                    reason += f" ({result['response_time']:.2f}s)"
            else:
                self.not_working_proxies.append(result)
                status = "❌"
                reason = result['reason']
            
            # Show progress
            progress = (self.progress_count / self.total_proxies) * 100
            print(f"[{progress:5.1f}%] {status} {result['proxy']} - {reason}")
    
    def test_proxies(self, proxy_list, max_workers=10, timeout=10):
        """Test multiple proxies with threading"""
        if not proxy_list:
            print("❌ No proxies to test!")
            return [], []
        
        self.total_proxies = len(proxy_list)
        self.progress_count = 0
        self.working_proxies = []
        self.not_working_proxies = []
        
        print(f"\n🔍 Testing {self.total_proxies} proxies...")
        print(f"⚙️  Settings: {max_workers} threads, {timeout}s timeout")
        print(f"📡 Target: http://httpbin.org/ip")
        print("=" * 60)
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_proxy = {
                executor.submit(self.test_single_proxy, proxy_data, timeout): proxy_data 
                for proxy_data in proxy_list
            }
            
            # Process completed tasks
            for future in as_completed(future_to_proxy):
                try:
                    result = future.result()
                    self.update_progress(result)
                except Exception as e:
                    proxy_data = future_to_proxy[future]
                    print(f"❌ {proxy_data['proxy']} - Unexpected error: {e}")
        
        total_time = time.time() - start_time
        
        print(f"\n📊 Testing Summary:")
        print(f"   ✅ Working: {len(self.working_proxies)}")
        print(f"   ❌ Not Working: {len(self.not_working_proxies)}")
        print(f"   📈 Success Rate: {(len(self.working_proxies)/self.total_proxies)*100:.1f}%")
        print(f"   ⏱️  Total Time: {total_time:.1f}s")
        
        return self.working_proxies, self.not_working_proxies
    
    def save_results(self, output_file, working_proxies, not_working_proxies, show_extra_info=False):
        """Save results to file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Header and working proxies
                f.write("# Working Proxy:Port\n")
                f.write("# These proxies respond with 403 Forbidden cloudflare or 400 Bad Request HTTPS port cloudflare\n")
                f.write(f"# Total: {len(working_proxies)} proxies\n")
                f.write("\n")
                
                if working_proxies:
                    # Sort by response time (fastest first)
                    working_sorted = sorted(working_proxies, key=lambda x: x['response_time'] if x['response_time'] else 999)
                    
                    for result in working_sorted:
                        line = result['proxy']
                        if show_extra_info and result['extra_info']:
                            line += f"  # {result['extra_info']}"
                        f.write(line + '\n')
                else:
                    f.write("# No working proxies found\n")
                
                f.write("\n")
                f.write("# " + "="*60 + "\n")
                f.write("\n")
                
                # Header and not working proxies
                f.write("# Not Working Proxy:Port\n")
                f.write("# These proxies did not respond with the required cloudflare responses\n")
                f.write(f"# Total: {len(not_working_proxies)} proxies\n")
                f.write("\n")
                
                if not_working_proxies:
                    # Sort by proxy string
                    not_working_sorted = sorted(not_working_proxies, key=lambda x: x['proxy'])
                    
                    for result in not_working_sorted:
                        line = result['proxy']
                        if show_extra_info and result['extra_info']:
                            line += f"  # {result['extra_info']}"
                        f.write(line + '\n')
                else:
                    f.write("# All proxies are working\n")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return False

def get_available_files():
    """Get available proxy files"""
    current_dir = Path('.')
    proxy_files = []
    
    # Common proxy file patterns
    patterns = ['*.txt', '*.list', '*.proxy']
    
    for pattern in patterns:
        for file_path in current_dir.glob(pattern):
            if file_path.is_file() and file_path.stat().st_size > 0:
                size_kb = file_path.stat().st_size / 1024
                proxy_files.append((str(file_path), size_kb))
    
    return sorted(proxy_files, key=lambda x: x[1], reverse=True)

def main():
    print("╔" + "="*60 + "╗")
    print("║" + " "*20 + "PROXY CHECKER" + " "*27 + "║")
    print("╚" + "="*60 + "╝")
    
    try:
        # Get available files
        print("\n🔍 Scanning for proxy files...")
        available_files = get_available_files()
        
        if not available_files:
            print("❌ No proxy files found in current directory!")
            return
        
        print(f"✅ Found {len(available_files)} proxy files:\n")
        
        for i, (file_path, size_kb) in enumerate(available_files, 1):
            print(f"   {i:2d}. {Path(file_path).name} ({size_kb:.1f} KB)")
        
        print(f"   {len(available_files)+1:2d}. 📁 Input path manual")
        print("    0. ❌ Exit")
        
        # File selection
        while True:
            try:
                choice = input(f"\nPilih file (1-{len(available_files)+1}) atau 0 untuk exit: ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    return
                elif choice == str(len(available_files)+1):
                    input_file = input("Masukkan path lengkap file: ").strip()
                    if not Path(input_file).exists():
                        print("❌ File tidak ditemukan!")
                        continue
                    break
                else:
                    file_index = int(choice) - 1
                    if 0 <= file_index < len(available_files):
                        input_file = available_files[file_index][0]
                        break
                    else:
                        print(f"❌ Pilihan harus antara 1-{len(available_files)+1}!")
                        continue
            except ValueError:
                print("❌ Input harus berupa angka!")
                continue
        
        print(f"✅ File dipilih: {Path(input_file).name}")
        
        # Preview file option
        preview = input("\n👁️  Preview file sebelum testing? (y/n): ").strip().lower()
        if preview == 'y':
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                print(f"\n📄 Preview {Path(input_file).name} (10 baris pertama):")
                print("-" * 50)
                for i, line in enumerate(lines, 1):
                    print(f"{i:2d}: {line.rstrip()}")
                if len(lines) == 10:
                    print("    ...")
                print("-" * 50)
            except Exception as e:
                print(f"❌ Error reading file: {e}")
        
        # Testing options
        print("\n" + "-" * 50)
        print("⚙️  TESTING OPTIONS")
        print("-" * 50)
        
        # Max workers
        while True:
            try:
                max_workers = input("\n1. Max Threads (default: 10): ").strip()
                if not max_workers:
                    max_workers = 10
                else:
                    max_workers = int(max_workers)
                    if max_workers < 1 or max_workers > 50:
                        print("❌ Threads harus antara 1-50!")
                        continue
                break
            except ValueError:
                print("❌ Input harus berupa angka!")
                continue
        
        # Timeout
        while True:
            try:
                timeout = input("2. Timeout per proxy (default: 10s): ").strip()
                if not timeout:
                    timeout = 10
                else:
                    timeout = int(timeout)
                    if timeout < 5 or timeout > 60:
                        print("❌ Timeout harus antara 5-60 detik!")
                        continue
                break
            except ValueError:
                print("❌ Input harus berupa angka!")
                continue
        
        # Show extra info option
        show_info = input("3. Show extra info in output file? (y/n, default: n): ").strip().lower()
        show_extra_info = show_info == 'y'
        
        # Output file
        default_output = f"proxy_check_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_file = input(f"4. Output file (default: {default_output}): ").strip()
        if not output_file:
            output_file = default_output
        
        # Summary
        print("\n" + "-" * 50)
        print("📋 TESTING SUMMARY")
        print("-" * 50)
        print(f"Input file: {Path(input_file).name}")
        print(f"Output file: {output_file}")
        print(f"Max threads: {max_workers}")
        print(f"Timeout: {timeout}s")
        print(f"Show extra info: {'Yes' if show_extra_info else 'No'}")
        
        confirm = input(f"\n🚀 Start testing? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Testing cancelled.")
            return
        
        # Initialize checker and load proxies
        checker = ProxyChecker()
        
        print(f"\n⏳ Loading proxies from {Path(input_file).name}...")
        proxy_list = checker.load_proxies_from_file(input_file)
        
        if not proxy_list:
            print("❌ No valid proxies found in file!")
            return
        
        # Test proxies
        working_proxies, not_working_proxies = checker.test_proxies(
            proxy_list, max_workers=max_workers, timeout=timeout
        )
        
        # Save results
        print(f"\n💾 Saving results to {output_file}...")
        if checker.save_results(output_file, working_proxies, not_working_proxies, show_extra_info):
            print(f"✅ Results saved successfully!")
            
            # Show working proxy examples
            if working_proxies:
                print(f"\n🎯 Working Proxies (first 5):")
                for result in working_proxies[:5]:
                    response_time = f" ({result['response_time']:.2f}s)" if result['response_time'] else ""
                    extra = result['extra_info'] if result['extra_info'] else ""
                    print(f"   ✅ {result['proxy']}{extra} - {result['reason']}{response_time}")
                
                if len(working_proxies) > 5:
                    print(f"   ... and {len(working_proxies) - 5} more working proxies")
            else:
                print(f"\n❌ No working proxies found!")
        else:
            print(f"❌ Failed to save results!")
        
        print(f"\n🎉 Testing completed! Results saved to: {Path(output_file).name}")
        
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
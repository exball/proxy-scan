#!/usr/bin/env python3
"""
Script Interaktif untuk mengekstrak proxy dan port dari berbagai file
dengan pilihan file yang fleksibel
"""

import re
import sys
import os
import time
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def is_valid_ip(ip_string):
    """Memeriksa apakah string adalah IP address yang valid"""
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return re.match(ip_pattern, ip_string.strip()) is not None

def extract_ip_from_line(line):
    """
    Mengekstrak IP address dari baris yang mungkin memiliki teks tambahan
    Menggunakan deteksi pola 3 titik tanpa spasi
    """
    line = line.strip()
    
    # Pola untuk mendeteksi IP address di awal baris
    ip_pattern = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    match = re.match(ip_pattern, line)
    
    if match:
        potential_ip = match.group(1)
        # Validasi apakah IP address benar-benar valid
        if is_valid_ip(potential_ip):
            return potential_ip
    
    return None

def scan_proxy_files(directory="/home/exball/Tunnel/proxy-scan"):
    """Scan directory untuk mencari file-file yang berpotensi sebagai proxy file"""
    
    proxy_files = []
    
    # Filter lebih spesifik untuk file proxy
    proxy_keywords = ['proxy', 'prox', 'socks', 'http']
    exclude_keywords = ['license', 'copyright', 'notice', 'thirdparty', 'node_modules']
    
    try:
        for file_path in Path(directory).rglob('*'):
            if file_path.is_file():
                file_name = file_path.name.lower()
                
                # Skip file yang tidak relevan
                if any(exclude in file_name for exclude in exclude_keywords):
                    continue
                
                # File harus .txt atau .list
                if not (file_name.endswith('.txt') or file_name.endswith('.list')):
                    continue
                
                # Cek ukuran file (skip file kosong atau terlalu kecil)
                if file_path.stat().st_size < 100:  # minimal 100 bytes
                    continue
                
                # Prioritaskan file yang mengandung kata 'proxy'
                if any(keyword in file_name for keyword in proxy_keywords):
                    proxy_files.append(str(file_path))
                # Atau file .txt/.list lainnya yang cukup besar
                elif file_path.stat().st_size > 1000:  # minimal 1KB untuk non-proxy files
                    proxy_files.append(str(file_path))
                    
    except Exception as e:
        print(f"Error scanning directory: {e}")
    
    # Sort: file dengan 'proxy' di nama dulu, lalu yang lain
    def sort_key(file_path):
        name = Path(file_path).name.lower()
        has_proxy = any(keyword in name for keyword in proxy_keywords)
        return (not has_proxy, name)  # not has_proxy supaya proxy files dulu
    
    return sorted(proxy_files, key=sort_key)

def preview_file(file_path, lines=10):
    """Preview beberapa baris pertama dari file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines_data = f.readlines()[:lines]
            
        print(f"\n--- Preview {file_path} ({len(lines_data)} baris pertama) ---")
        for i, line in enumerate(lines_data, 1):
            print(f"{i:2d}: {line.rstrip()}")
        print("--- End Preview ---\n")
        
    except Exception as e:
        print(f"Error previewing file: {e}")

def test_single_proxy(proxy_port, separator, timeout=10):
    """Test single proxy and return result"""
    try:
        if separator == ",":
            ip, port = proxy_port.split(",")
        elif separator == ":":
            ip, port = proxy_port.split(":")
        else:  # space
            ip, port = proxy_port.split(" ")
        
        # Test URL - using HTTP to trigger the specific responses you need
        test_url = "http://httpbin.org/ip"
        
        proxies = {
            'http': f'http://{ip}:{port}',
            'https': f'http://{ip}:{port}'
        }
        
        start_time = time.time()
        response = requests.get(test_url, proxies=proxies, timeout=timeout)
        response_time = time.time() - start_time
        
        # Check response content
        response_text = response.text.lower()
        response_headers = str(response.headers).lower()
        
        # Check for your specific working conditions
        is_working = False
        status_reason = ""
        
        if response.status_code == 403 and 'cloudflare' in (response_text + response_headers):
            is_working = True
            status_reason = "403 Forbidden cloudflare"
        elif response.status_code == 400 and 'https port' in response_text and 'cloudflare' in (response_text + response_headers):
            is_working = True
            status_reason = "400 Bad Request HTTPS port cloudflare"
        else:
            status_reason = f"{response.status_code} - Other response"
        
        return {
            'proxy': proxy_port,
            'working': is_working,
            'status_code': response.status_code,
            'response_time': response_time,
            'reason': status_reason,
            'error': None
        }
        
    except requests.exceptions.ProxyError:
        return {
            'proxy': proxy_port,
            'working': False,
            'status_code': None,
            'response_time': None,
            'reason': "Proxy connection failed",
            'error': "ProxyError"
        }
    except requests.exceptions.Timeout:
        return {
            'proxy': proxy_port,
            'working': False,
            'status_code': None,
            'response_time': None,
            'reason': "Request timeout",
            'error': "Timeout"
        }
    except requests.exceptions.ConnectionError:
        return {
            'proxy': proxy_port,
            'working': False,
            'status_code': None,
            'response_time': None,
            'reason': "Connection error",
            'error': "ConnectionError"
        }
    except Exception as e:
        return {
            'proxy': proxy_port,
            'working': False,
            'status_code': None,
            'response_time': None,
            'reason': f"Unexpected error: {str(e)[:50]}",
            'error': "Exception"
        }

def test_proxy_list(proxy_ports, separator, max_workers=10, timeout=10):
    """Test list of proxies with threading"""
    print(f"\n🔍 Testing {len(proxy_ports)} proxies...")
    print(f"⚙️  Settings: {max_workers} threads, {timeout}s timeout")
    print(f"📡 Target: http://httpbin.org/ip")
    print("=" * 60)
    
    working_proxies = []
    not_working_proxies = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_proxy = {
            executor.submit(test_single_proxy, proxy, separator, timeout): proxy 
            for proxy in proxy_ports
        }
        
        completed = 0
        total = len(proxy_ports)
        
        # Process completed tasks
        for future in as_completed(future_to_proxy):
            completed += 1
            result = future.result()
            
            # Progress indicator
            progress = (completed / total) * 100
            
            if result['working']:
                working_proxies.append(result)
                print(f"✅ {result['proxy']} - {result['reason']} ({result['response_time']:.2f}s)")
            else:
                not_working_proxies.append(result)
                print(f"❌ {result['proxy']} - {result['reason']}")
    
    print(f"\n📊 Testing Summary:")
    print(f"   ✅ Working: {len(working_proxies)}")
    print(f"   ❌ Not Working: {len(not_working_proxies)}")
    print(f"   📈 Success Rate: {(len(working_proxies)/total)*100:.1f}%")
    
    return working_proxies, not_working_proxies

def save_proxy_results(output_file, working_proxies, not_working_proxies):
    """Save proxy results with grouping"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header and working proxies
            f.write("# Working Proxy:Port\n")
            f.write("# These proxies respond with 403 Forbidden cloudflare or 400 Bad Request HTTPS port cloudflare\n")
            f.write(f"# Total: {len(working_proxies)} proxies\n")
            f.write("\n")
            
            if working_proxies:
                # Sort working proxies by response time (fastest first)
                working_sorted = sorted(working_proxies, key=lambda x: x['response_time'] if x['response_time'] else 999)
                
                for result in working_sorted:
                    f.write(f"{result['proxy']}\n")
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
                # Sort not working proxies by proxy string
                not_working_sorted = sorted(not_working_proxies, key=lambda x: x['proxy'])
                
                for result in not_working_sorted:
                    f.write(f"{result['proxy']}\n")
            else:
                f.write("# All proxies are working\n")
        
        return True
        
    except Exception as e:
        print(f"Error saving results: {e}")
        return False

def extract_proxy_ports(input_file, output_file, port_filter=None, format_type="comma"):
    """
    Mengekstrak proxy dan port dari file input
    Mendukung dua format:
    1. Format proxy-sg.txt: IP diawali spasi, port format "443/HTTP"
    2. Format Untitled-1.txt: IP tanpa spasi, port format "443 / HTTP"
    """
    
    if not Path(input_file).exists():
        print(f"Error: File {input_file} tidak ditemukan!")
        return False
    
    proxy_ports = []
    current_proxy = None
    
    # Tentukan separator berdasarkan format
    separators = {
        "comma": ",",
        "colon": ":",
        "space": " "
    }
    separator = separators.get(format_type, ",")
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Cek apakah line ini adalah IP address (proxy)
            # Menggunakan extract_ip_from_line untuk menangani IP dengan teks tambahan
            
            # Format 1: IP diawali dengan spasi (proxy-sg.txt)
            if original_line.startswith(' '):
                extracted_ip = extract_ip_from_line(line)
                if extracted_ip:
                    current_proxy = extracted_ip
                    continue
            
            # Format 2: IP tanpa spasi di awal (Untitled-1.txt dan format baru dengan teks tambahan)
            else:
                extracted_ip = extract_ip_from_line(line)
                if extracted_ip:
                    current_proxy = extracted_ip
                    continue
            
            # Cek apakah line ini adalah port
            if current_proxy:
                port_match = None
                
                # Format 1: "443/HTTP" (proxy-sg.txt)
                if '/HTTP' in line and ' / ' not in line:
                    port_match = re.search(r'(\d+)/HTTP', line)
                
                # Format 2: "443 / HTTP" (Untitled-1.txt)
                elif ' / HTTP' in line:
                    port_match = re.search(r'(\d+) / HTTP', line)
                
                if port_match:
                    port = port_match.group(1)
                    
                    # Filter port jika ada filter
                    if port_filter is None or port in port_filter:
                        proxy_ports.append(f"{current_proxy}{separator}{port}")
        
        # Urutkan hasil berdasarkan PORT terlebih dahulu (bukan IP)
        def sort_key(proxy_port_str):
            try:
                # Split berdasarkan separator
                if separator == ",":
                    ip, port = proxy_port_str.split(",")
                elif separator == ":":
                    ip, port = proxy_port_str.split(":")
                else:  # space
                    ip, port = proxy_port_str.split(" ")
                
                # Urutkan berdasarkan PORT terlebih dahulu, kemudian IP
                port_num = int(port)
                ip_parts = tuple(int(part) for part in ip.split('.'))
                
                return (port_num, ip_parts)  # Port dulu, baru IP
            except:
                return (99999, tuple([999, 999, 999, 999]))  # fallback untuk error
        
        # Sort proxy_ports berdasarkan PORT terlebih dahulu
        proxy_ports_sorted = sorted(proxy_ports, key=sort_key)
        
        # Remove duplicates while preserving order
        proxy_ports_unique = []
        seen = set()
        
        for proxy_port in proxy_ports_sorted:
            if proxy_port not in seen:
                proxy_ports_unique.append(proxy_port)
                seen.add(proxy_port)
        
        # Show deduplication statistics
        total_combinations = len(proxy_ports_sorted)
        unique_combinations = len(proxy_ports_unique)
        duplicates_removed = total_combinations - unique_combinations
        
        if duplicates_removed > 0:
            print(f"🗑️  Duplikat dihapus: {duplicates_removed} dari {total_combinations} kombinasi")
            print(f"🎯 Unique kombinasi: {unique_combinations}")
        
        return proxy_ports_unique
        
    except Exception as e:
        print(f"Error saat memproses file: {e}")
        return False

def show_file_selection_menu():
    """Menampilkan menu pemilihan file"""
    
    print("╔" + "═" * 60 + "╗")
    print("║" + " " * 18 + "PROXY EXTRACTOR" + " " * 25 + "║")
    print("╚" + "═" * 60 + "╝")
    print()
    
    # Scan file-file proxy yang tersedia
    print("🔍 Scanning untuk file proxy...")
    proxy_files = scan_proxy_files()
    
    if not proxy_files:
        print("❌ Tidak ditemukan file proxy di direktori ini.")
        print("💡 Pastikan ada file .txt atau .list yang berisi data proxy.")
        return None
    
    print(f"✅ Ditemukan {len(proxy_files)} file potensial:\n")
    
    # Tampilkan daftar file
    for i, file_path in enumerate(proxy_files, 1):
        file_name = Path(file_path).name
        file_size = Path(file_path).stat().st_size
        file_size_kb = file_size / 1024
        print(f"  {i:2d}. {file_name} ({file_size_kb:.1f} KB)")
    
    print(f"  {len(proxy_files) + 1:2d}. 📁 Input path manual")
    print(f"  {len(proxy_files) + 2:2d}. 👁️  Preview file sebelum memilih")
    print("   0. ❌ Exit")
    print()
    
    while True:
        try:
            choice = input(f"Pilih file (1-{len(proxy_files) + 2}) atau 0 untuk exit: ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                return None
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(proxy_files):
                return proxy_files[choice_num - 1]
            
            elif choice_num == len(proxy_files) + 1:
                # Input manual
                manual_path = input("Masukkan path lengkap file: ").strip()
                if Path(manual_path).exists():
                    return manual_path
                else:
                    print("❌ File tidak ditemukan!")
                    continue
            
            elif choice_num == len(proxy_files) + 2:
                # Preview file
                preview_choice = input(f"Pilih nomor file untuk preview (1-{len(proxy_files)}): ").strip()
                try:
                    preview_num = int(preview_choice)
                    if 1 <= preview_num <= len(proxy_files):
                        preview_file(proxy_files[preview_num - 1])
                    else:
                        print("❌ Nomor tidak valid!")
                except ValueError:
                    print("❌ Input harus berupa angka!")
                continue
            
            else:
                print("❌ Pilihan tidak valid!")
                continue
                
        except ValueError:
            print("❌ Input harus berupa angka!")
            continue
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return None

def show_extraction_options():
    """Menampilkan opsi ekstraksi"""
    
    print("\n" + "─" * 50)
    print("⚙️  OPSI EKSTRAKSI")
    print("─" * 50)
    
    # Format output
    print("\n1. Format Output:")
    print("   1. Comma (IP,PORT)")
    print("   2. Colon (IP:PORT)")
    print("   3. Space (IP PORT)")
    
    format_choice = input("\nPilih format (1-3, default: 1): ").strip() or "1"
    formats = {"1": "comma", "2": "colon", "3": "space"}
    output_format = formats.get(format_choice, "comma")
    
    # Port filter
    print("\n2. Filter Port:")
    print("   Kosong = semua port HTTP")
    print("   Contoh: 443,8080,8888")
    
    port_input = input("\nMasukkan port (pisahkan dengan koma): ").strip()
    port_filter = None
    if port_input:
        port_filter = [p.strip() for p in port_input.split(',')]
    
    # Test proxy option
    print("\n3. Test Proxy Connectivity:")
    print("   Test setiap proxy untuk respon '403 Forbidden cloudflare' atau")
    print("   '400 Bad Request HTTPS port cloudflare' menggunakan http://httpbin.org/ip")
    print("   ⚠️  Warning: Testing akan memakan waktu lebih lama!")
    
    test_choice = input("\nTest proxy connectivity? (y/n, default: n): ").strip().lower()
    test_proxies = test_choice in ['y', 'yes']
    
    # Test settings if enabled
    max_workers = 10
    timeout = 10
    if test_proxies:
        print("\n   📊 Test Settings:")
        workers_input = input("   Max concurrent threads (default: 10): ").strip()
        if workers_input.isdigit():
            max_workers = int(workers_input)
        
        timeout_input = input("   Timeout per proxy in seconds (default: 10): ").strip()
        if timeout_input.isdigit():
            timeout = int(timeout_input)
    
    # Output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_output = f"/home/exball/Tunnel/proxy-scan/extracted_proxy_{timestamp}.txt"
    
    print(f"\n4. Output file:")
    print(f"   Default: extracted_proxy_{timestamp}.txt")
    output_file = input("\nNama file output (kosong untuk default): ").strip()
    
    if not output_file:
        output_file = default_output
    elif not output_file.startswith('/'):
        # Jika tidak absolute path, tambahkan direktori default
        output_file = f"/home/exball/Tunnel/proxy-scan/{output_file}"
    
    return {
        'format': output_format,
        'port_filter': port_filter,
        'test_proxies': test_proxies,
        'max_workers': max_workers,
        'timeout': timeout,
        'output_file': output_file
    }

def main():
    """Fungsi utama"""
    
    try:
        # Pilih file input
        input_file = show_file_selection_menu()
        if not input_file:
            return
        
        print(f"\n✅ File dipilih: {Path(input_file).name}")
        
        # Tanya apakah ingin preview file
        preview_choice = input("\n👁️  Preview file sebelum ekstraksi? (y/n): ").strip().lower()
        if preview_choice in ['y', 'yes']:
            preview_file(input_file)
        
        # Dapatkan opsi ekstraksi
        options = show_extraction_options()
        
        # Konfirmasi
        print("\n" + "─" * 50)
        print("📋 RINGKASAN EKSTRAKSI")
        print("─" * 50)
        print(f"Input file: {Path(input_file).name}")
        print(f"Output file: {Path(options['output_file']).name}")
        print(f"Format: {options['format']}")
        print(f"Port filter: {options['port_filter'] if options['port_filter'] else 'Semua HTTP port'}")
        print(f"Test proxies: {'Ya' if options['test_proxies'] else 'Tidak'}")
        if options['test_proxies']:
            print(f"  - Max threads: {options['max_workers']}")
            print(f"  - Timeout: {options['timeout']}s")
        
        confirm = input(f"\n🚀 Lanjutkan ekstraksi? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Ekstraksi dibatalkan.")
            return
        
        # Jalankan ekstraksi
        print("\n⏳ Sedang memproses ekstraksi...")
        
        proxy_ports = extract_proxy_ports(
            input_file,
            None,  # Don't save to file yet
            options['port_filter'],
            options['format']
        )
        
        if proxy_ports:
            print("\n" + "="*50)
            print("✅ EKSTRAKSI BERHASIL!")
            print("="*50)
            print(f"📊 Final kombinasi proxy:port: {len(proxy_ports)}")
            
            # Hitung proxy unik
            separator = {"comma": ",", "colon": ":", "space": " "}[options['format']]
            unique_proxies = len(set(pp.split(separator)[0] for pp in proxy_ports))
            print(f"🌐 Unique IP addresses: {unique_proxies}")
            print(f"🎯 Ready untuk testing: {len(proxy_ports)} kombinasi")
            
            # Test proxies if requested
            if options['test_proxies']:
                working_proxies, not_working_proxies = test_proxy_list(
                    proxy_ports, 
                    separator, 
                    options['max_workers'], 
                    options['timeout']
                )
                
                # Save results with grouping
                if save_proxy_results(options['output_file'], working_proxies, not_working_proxies):
                    print(f"\n💾 Results saved with grouping to: {Path(options['output_file']).name}")
                    
                    # Show working proxy examples
                    if working_proxies:
                        print(f"\n🎯 Working Proxies (first 5):")
                        for result in working_proxies[:5]:
                            response_time = f" ({result['response_time']:.2f}s)" if result['response_time'] else ""
                            print(f"   ✅ {result['proxy']} - {result['reason']}{response_time}")
                        
                        if len(working_proxies) > 5:
                            print(f"   ... and {len(working_proxies) - 5} more working proxies")
                    else:
                        print(f"\n❌ No working proxies found!")
                        
            else:
                # Save without testing (simple format)
                with open(options['output_file'], 'w', encoding='utf-8') as f:
                    for proxy_port in proxy_ports:
                        f.write(proxy_port + '\n')
                
                print(f"💾 File output: {options['output_file']}")
                
                # Tampilkan contoh hasil
                print(f"\n📝 Contoh hasil (5 baris pertama):")
                for i, proxy_port in enumerate(proxy_ports[:5]):
                    print(f"   {proxy_port}")
                
                if len(proxy_ports) > 5:
                    print(f"   ... dan {len(proxy_ports) - 5} lainnya")
            
            print(f"\n🎉 Selesai! File tersimpan di: {Path(options['output_file']).name}")
            
        else:
            print("\n❌ Tidak ada data yang berhasil diekstrak!")
            print("💡 Periksa format file input atau coba dengan file lain.")
    
    except KeyboardInterrupt:
        print("\n\n👋 Program dihentikan oleh user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
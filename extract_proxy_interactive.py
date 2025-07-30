#!/usr/bin/env python3
"""
Script Interaktif untuk mengekstrak proxy dan port dari berbagai file
dengan pilihan file yang fleksibel
"""

import re
import sys
import os
from pathlib import Path
from datetime import datetime

def is_valid_ip(ip_string):
    """Memeriksa apakah string adalah IP address yang valid"""
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return re.match(ip_pattern, ip_string.strip()) is not None

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

def extract_proxy_ports(input_file, output_file, port_filter=None, include_ssh=False, format_type="comma"):
    """
    Mengekstrak proxy dan port dari file input
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
            if original_line.startswith(' ') and is_valid_ip(line):
                current_proxy = line
                continue
            
            # Cek apakah line ini adalah port
            if current_proxy:
                port_match = None
                
                # Cek port HTTP
                if '/HTTP' in line:
                    port_match = re.search(r'(\d+)/HTTP', line)
                
                # Cek port SSH jika diminta
                elif include_ssh and '/SSH' in line:
                    port_match = re.search(r'(\d+)/SSH', line)
                
                if port_match:
                    port = port_match.group(1)
                    
                    # Filter port jika ada filter
                    if port_filter is None or port in port_filter:
                        proxy_ports.append(f"{current_proxy}{separator}{port}")
        
        # Simpan hasil ke file output
        with open(output_file, 'w', encoding='utf-8') as f:
            for proxy_port in proxy_ports:
                f.write(proxy_port + '\n')
        
        return proxy_ports
        
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
    
    # Include SSH
    ssh_choice = input("\n3. Include SSH port? (y/n, default: n): ").strip().lower()
    include_ssh = ssh_choice in ['y', 'yes']
    
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
        'include_ssh': include_ssh,
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
        print(f"Include SSH: {'Ya' if options['include_ssh'] else 'Tidak'}")
        
        confirm = input(f"\n🚀 Lanjutkan ekstraksi? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Ekstraksi dibatalkan.")
            return
        
        # Jalankan ekstraksi
        print("\n⏳ Sedang memproses...")
        
        proxy_ports = extract_proxy_ports(
            input_file,
            options['output_file'],
            options['port_filter'],
            options['include_ssh'],
            options['format']
        )
        
        if proxy_ports:
            print("\n" + "="*50)
            print("✅ EKSTRAKSI BERHASIL!")
            print("="*50)
            print(f"📊 Total kombinasi proxy:port: {len(proxy_ports)}")
            
            # Hitung proxy unik
            separator = {"comma": ",", "colon": ":", "space": " "}[options['format']]
            unique_proxies = len(set(pp.split(separator)[0] for pp in proxy_ports))
            print(f"🌐 Proxy unik: {unique_proxies}")
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
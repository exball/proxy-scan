#!/usr/bin/env python3
"""
Script Interaktif untuk Ekstraksi IP:Port dari File Shodan
Menampilkan pilihan file yang tersedia untuk dipilih
"""

import os
import re
import glob
from datetime import datetime

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    """Tampilkan banner aplikasi"""
    print("=" * 60)
    print("🔍 SCRIPT EKSTRAKSI IP:PORT DARI FILE SHODAN")
    print("=" * 60)
    print("📅 Dibuat untuk mengekstrak data Shodan ke format IP,PORT")
    print("🎯 Format output: IP,PORT (satu kombinasi per baris)")
    print("=" * 60)

def find_text_files():
    """Cari semua file .txt di direktori saat ini"""
    txt_files = []
    
    # Cari file .txt di direktori saat ini
    for file in glob.glob("*.txt"):
        if os.path.isfile(file):
            size = os.path.getsize(file)
            size_mb = size / (1024 * 1024)
            modified = datetime.fromtimestamp(os.path.getmtime(file))
            txt_files.append({
                'name': file,
                'size': size,
                'size_mb': size_mb,
                'modified': modified.strftime('%Y-%m-%d %H:%M')
            })
    
    # Sort berdasarkan nama file
    txt_files.sort(key=lambda x: x['name'])
    return txt_files

def show_file_list(files):
    """Tampilkan daftar file yang tersedia"""
    print("\n📁 FILE .TXT YANG TERSEDIA:")
    print("-" * 60)
    print(f"{'No':<3} {'Nama File':<25} {'Ukuran':<10} {'Terakhir Diubah'}")
    print("-" * 60)
    
    for i, file_info in enumerate(files, 1):
        size_str = f"{file_info['size_mb']:.1f} MB" if file_info['size_mb'] >= 1 else f"{file_info['size']} B"
        print(f"{i:<3} {file_info['name']:<25} {size_str:<10} {file_info['modified']}")
    
    print("-" * 60)

def get_user_choice(max_choice):
    """Dapatkan pilihan user dengan validasi"""
    while True:
        try:
            print(f"\n🎯 Pilihan yang tersedia:")
            print(f"   1-{max_choice}: Pilih file untuk diekstrak")
            print(f"   0: Keluar dari program")
            print(f"   r: Refresh daftar file")
            
            choice = input(f"\n👉 Masukkan pilihan Anda (0-{max_choice}/r): ").strip().lower()
            
            if choice == '0':
                return 0
            elif choice == 'r':
                return 'refresh'
            elif choice.isdigit():
                num = int(choice)
                if 1 <= num <= max_choice:
                    return num
                else:
                    print(f"❌ Pilihan harus antara 1-{max_choice}!")
            else:
                print("❌ Input tidak valid! Masukkan angka atau 'r' untuk refresh.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Program dihentikan oleh user.")
            return 0
        except Exception as e:
            print(f"❌ Error: {e}")

def extract_ip_port(input_file):
    """Ekstrak IP dan Port dari file Shodan"""
    results = []
    current_ip = None
    
    try:
        print(f"\n🔄 Membaca file: {input_file}")
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()
        
        print(f"📄 Total baris dalam file: {len(lines)}")
        print("🔍 Memproses data...")
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Progress indicator setiap 100 baris
            if i % 100 == 0 and i > 0:
                print(f"   📊 Memproses baris {i}/{len(lines)} ({i/len(lines)*100:.1f}%)")
            
            # Cari IP address setelah kata "Account"
            if line == "Account" and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                ip_match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*$', next_line)
                if ip_match:
                    current_ip = ip_match.group(1)
                    print(f"   🎯 Ditemukan IP: {current_ip}")
            
            # Cari port dalam format "PORT / tcp"
            if current_ip and " / tcp" in line:
                port_match = re.match(r'^(\d+)\s*/\s*tcp', line)
                if port_match:
                    port = port_match.group(1)
                    results.append((current_ip, port))
            
            # Reset current_ip ketika menemukan separator
            if line.startswith("----"):
                current_ip = None
        
        return results
        
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' tidak ditemukan!")
        return []
    except Exception as e:
        print(f"❌ Error membaca file: {e}")
        return []

def generate_output_filename(input_file):
    """Generate nama file output berdasarkan input file"""
    base_name = os.path.splitext(input_file)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"extracted_{base_name}_{timestamp}.txt"

def save_results(results, output_file):
    """Simpan hasil ekstraksi ke file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            for ip, port in results:
                file.write(f"{ip},{port}\n")
        return True
    except Exception as e:
        print(f"❌ Error menyimpan file: {e}")
        return False

def show_results_summary(results, output_file):
    """Tampilkan ringkasan hasil ekstraksi"""
    if not results:
        print("\n❌ Tidak ada data IP:Port yang ditemukan!")
        return
    
    # Hitung statistik
    unique_ips = set(ip for ip, port in results)
    ip_port_count = {}
    
    for ip, port in results:
        if ip not in ip_port_count:
            ip_port_count[ip] = []
        ip_port_count[ip].append(port)
    
    print("\n" + "=" * 60)
    print("✅ HASIL EKSTRAKSI")
    print("=" * 60)
    print(f"📄 File output: {output_file}")
    print(f"🎯 Total kombinasi IP:Port: {len(results)}")
    print(f"🌐 Total IP unik: {len(unique_ips)}")
    
    print(f"\n📋 PREVIEW HASIL (10 baris pertama):")
    print("-" * 30)
    for i, (ip, port) in enumerate(results[:10]):
        print(f"{ip},{port}")
    
    if len(results) > 10:
        print(f"... dan {len(results) - 10} kombinasi lainnya")
    
    print(f"\n📊 STATISTIK PER IP:")
    print("-" * 40)
    for ip in sorted(unique_ips):
        ports = sorted(ip_port_count[ip], key=int)
        print(f"🔹 {ip}: {len(ports)} ports ({', '.join(ports[:5])}{'...' if len(ports) > 5 else ''})")
    
    print("\n💡 TIPS PENGGUNAAN:")
    print(f"   • Lihat semua hasil: cat {output_file}")
    print(f"   • Lihat IP unik: cut -d',' -f1 {output_file} | sort -u")
    print(f"   • Filter port 80: grep ',80$' {output_file}")

def main():
    """Fungsi utama program"""
    while True:
        clear_screen()
        show_banner()
        
        # Cari file .txt
        files = find_text_files()
        
        if not files:
            print("\n❌ Tidak ada file .txt yang ditemukan di direktori ini!")
            print("💡 Pastikan file Shodan (.txt) ada di direktori yang sama dengan script ini.")
            input("\n📱 Tekan Enter untuk keluar...")
            break
        
        # Tampilkan daftar file
        show_file_list(files)
        
        # Dapatkan pilihan user
        choice = get_user_choice(len(files))
        
        if choice == 0:
            print("\n👋 Terima kasih telah menggunakan script ini!")
            break
        elif choice == 'refresh':
            continue
        
        # Proses file yang dipilih
        selected_file = files[choice - 1]['name']
        print(f"\n🎯 File yang dipilih: {selected_file}")
        
        # Konfirmasi
        confirm = input("📝 Lanjutkan ekstraksi? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes', 'ya']:
            continue
        
        # Ekstrak data
        results = extract_ip_port(selected_file)
        
        if results:
            # Generate nama file output
            output_file = generate_output_filename(selected_file)
            
            # Simpan hasil
            if save_results(results, output_file):
                show_results_summary(results, output_file)
            else:
                print("❌ Gagal menyimpan hasil ekstraksi!")
        else:
            print("\n❌ Tidak ada data yang berhasil diekstrak!")
        
        # Tanya apakah ingin memproses file lain
        print("\n" + "=" * 60)
        another = input("🔄 Proses file lain? (y/n): ").strip().lower()
        if another not in ['y', 'yes', 'ya']:
            print("\n👋 Terima kasih telah menggunakan script ini!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program dihentikan oleh user. Sampai jumpa!")
    except Exception as e:
        print(f"\n❌ Error tidak terduga: {e}")
        print("💡 Silakan laporkan error ini jika terus terjadi.")
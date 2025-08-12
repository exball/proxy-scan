#!/usr/bin/env python3
"""
🔍 SCRIPT EKSTRAKSI IP:PORT DARI FILE SHODAN - VERSI FINAL
Menampilkan menu interaktif untuk memilih file yang akan diekstrak
"""

import os
import re
import glob
import subprocess
from datetime import datetime

class Colors:
    """Kelas untuk warna terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    """Tampilkan banner aplikasi"""
    print(f"{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.YELLOW}🔍 SCRIPT EKSTRAKSI IP:PORT DARI FILE SHODAN{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.GREEN}📅 Mengekstrak data Shodan ke format IP,PORT{Colors.ENDC}")
    print(f"{Colors.GREEN}🎯 Output: IP,PORT (satu kombinasi per baris){Colors.ENDC}")
    print(f"{Colors.GREEN}⚡ Versi: Final Interactive v1.0{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.ENDC}")

def find_text_files():
    """Cari dan analisis file .txt di direktori saat ini"""
    txt_files = []
    
    for file in glob.glob("*.txt"):
        if os.path.isfile(file):
            try:
                size = os.path.getsize(file)
                modified = datetime.fromtimestamp(os.path.getmtime(file))
                
                # Cek apakah file berisi data Shodan (cari kata "Account")
                is_shodan = False
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(1000)  # Baca 1000 karakter pertama
                        if 'Account' in content and ('/ tcp' in content or 'Shodan' in content):
                            is_shodan = True
                except:
                    pass
                
                txt_files.append({
                    'name': file,
                    'size': size,
                    'modified': modified,
                    'is_shodan': is_shodan
                })
            except:
                continue
    
    # Sort berdasarkan: Shodan files dulu, lalu berdasarkan nama
    txt_files.sort(key=lambda x: (not x['is_shodan'], x['name']))
    return txt_files

def format_size(size_bytes):
    """Format ukuran file menjadi human readable"""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"

def show_file_list(files):
    """Tampilkan daftar file dengan informasi detail"""
    print(f"\n{Colors.BLUE}📁 FILE .TXT YANG TERSEDIA:{Colors.ENDC}")
    print("-" * 70)
    print(f"{'No':<3} {'Nama File':<30} {'Ukuran':<10} {'Tipe':<8} {'Terakhir Diubah'}")
    print("-" * 70)
    
    for i, file_info in enumerate(files, 1):
        size_str = format_size(file_info['size'])
        modified_str = file_info['modified'].strftime('%Y-%m-%d %H:%M')
        type_str = f"{Colors.GREEN}Shodan{Colors.ENDC}" if file_info['is_shodan'] else "Text"
        
        # Highlight file Shodan
        if file_info['is_shodan']:
            print(f"{Colors.GREEN}{i:<3} {file_info['name']:<30} {size_str:<10}{Colors.ENDC} {type_str:<15} {modified_str}")
        else:
            print(f"{i:<3} {file_info['name']:<30} {size_str:<10} {type_str:<15} {modified_str}")
    
    print("-" * 70)
    
    # Tampilkan legend
    shodan_count = sum(1 for f in files if f['is_shodan'])
    print(f"{Colors.YELLOW}💡 Ditemukan {shodan_count} file Shodan dan {len(files) - shodan_count} file text lainnya{Colors.ENDC}")

def get_user_choice(max_choice):
    """Dapatkan pilihan user dengan validasi"""
    while True:
        try:
            print(f"\n{Colors.YELLOW}🎯 Pilihan yang tersedia:{Colors.ENDC}")
            print(f"   {Colors.GREEN}1-{max_choice}{Colors.ENDC}: Pilih file untuk diekstrak")
            print(f"   {Colors.RED}0{Colors.ENDC}: Keluar dari program")
            print(f"   {Colors.BLUE}r{Colors.ENDC}: Refresh daftar file")
            print(f"   {Colors.CYAN}h{Colors.ENDC}: Tampilkan bantuan")
            
            choice = input(f"\n{Colors.BOLD}👉 Masukkan pilihan Anda: {Colors.ENDC}").strip().lower()
            
            if choice == '0':
                return 0
            elif choice in ['r', 'refresh']:
                return 'refresh'
            elif choice in ['h', 'help']:
                return 'help'
            elif choice.isdigit():
                num = int(choice)
                if 1 <= num <= max_choice:
                    return num
                else:
                    print(f"{Colors.RED}❌ Pilihan harus antara 1-{max_choice}!{Colors.ENDC}")
            else:
                print(f"{Colors.RED}❌ Input tidak valid! Masukkan angka, 'r', atau 'h'.{Colors.ENDC}")
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}👋 Program dihentikan oleh user.{Colors.ENDC}")
            return 0
        except Exception as e:
            print(f"{Colors.RED}❌ Error: {e}{Colors.ENDC}")

def show_help():
    """Tampilkan bantuan penggunaan"""
    print(f"\n{Colors.CYAN}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.YELLOW}📖 BANTUAN PENGGUNAAN{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.GREEN}🎯 Cara Menggunakan:{Colors.ENDC}")
    print("   1. Pilih nomor file yang ingin diekstrak")
    print("   2. Konfirmasi pilihan dengan 'y' atau 'yes'")
    print("   3. Script akan mengekstrak IP:Port secara otomatis")
    print("   4. Hasil disimpan dalam file baru dengan timestamp")
    
    print(f"\n{Colors.GREEN}📋 Format Input yang Didukung:{Colors.ENDC}")
    print("   • File export dari Shodan")
    print("   • File yang berisi kata 'Account' dan 'PORT / tcp'")
    print("   • Format text dengan struktur Shodan")
    
    print(f"\n{Colors.GREEN}📄 Format Output:{Colors.ENDC}")
    print("   • IP,PORT (satu kombinasi per baris)")
    print("   • Contoh: 192.168.1.1,80")
    
    print(f"\n{Colors.GREEN}💡 Tips:{Colors.ENDC}")
    print("   • File dengan label 'Shodan' lebih direkomendasikan")
    print("   • Gunakan 'r' untuk refresh jika ada file baru")
    print("   • File output otomatis diberi timestamp")
    
    input(f"\n{Colors.BLUE}📱 Tekan Enter untuk kembali...{Colors.ENDC}")

def generate_output_filename(input_file):
    """Generate nama file output dengan timestamp"""
    base_name = os.path.splitext(input_file)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"extracted_{base_name}_{timestamp}.txt"

def extract_with_progress(input_file, output_file):
    """Ekstrak file dengan menampilkan progress"""
    print(f"\n{Colors.BLUE}🔄 Memproses file: {input_file}{Colors.ENDC}")
    print(f"{Colors.BLUE}📄 Output akan disimpan ke: {output_file}{Colors.ENDC}")
    
    try:
        # Jalankan script ekstraksi
        result = subprocess.run(['python3', 'extract_simple.py', input_file, output_file], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        return False, "Timeout: File terlalu besar atau proses terlalu lama"
    except Exception as e:
        return False, str(e)

def show_results_summary(output_file):
    """Tampilkan ringkasan hasil ekstraksi"""
    if not os.path.exists(output_file):
        print(f"{Colors.RED}❌ File output tidak ditemukan!{Colors.ENDC}")
        return
    
    try:
        with open(output_file, 'r') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        unique_ips = len(set(line.split(',')[0] for line in lines if ',' in line))
        
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.GREEN}✅ HASIL EKSTRAKSI{Colors.ENDC}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.BLUE}📄 File output: {output_file}{Colors.ENDC}")
        print(f"{Colors.BLUE}🎯 Total kombinasi IP:Port: {total_lines}{Colors.ENDC}")
        print(f"{Colors.BLUE}🌐 Total IP unik: {unique_ips}{Colors.ENDC}")
        
        # Preview hasil
        print(f"\n{Colors.YELLOW}📋 PREVIEW HASIL (10 baris pertama):{Colors.ENDC}")
        print("-" * 30)
        for i, line in enumerate(lines[:10]):
            print(f"{Colors.GREEN}{line.strip()}{Colors.ENDC}")
        
        if total_lines > 10:
            print(f"{Colors.YELLOW}... dan {total_lines - 10} kombinasi lainnya{Colors.ENDC}")
        
        # Tips penggunaan
        print(f"\n{Colors.YELLOW}💡 TIPS PENGGUNAAN:{Colors.ENDC}")
        print(f"   • Lihat semua hasil: {Colors.GREEN}cat {output_file}{Colors.ENDC}")
        print(f"   • Lihat IP unik: {Colors.GREEN}cut -d',' -f1 {output_file} | sort -u{Colors.ENDC}")
        print(f"   • Filter port 80: {Colors.GREEN}grep ',80$' {output_file}{Colors.ENDC}")
        print(f"   • Hitung total: {Colors.GREEN}wc -l {output_file}{Colors.ENDC}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error membaca hasil: {e}{Colors.ENDC}")

def main():
    """Fungsi utama program"""
    while True:
        clear_screen()
        show_banner()
        
        # Cari file .txt
        files = find_text_files()
        
        if not files:
            print(f"\n{Colors.RED}❌ Tidak ada file .txt yang ditemukan di direktori ini!{Colors.ENDC}")
            print(f"{Colors.YELLOW}💡 Pastikan file Shodan (.txt) ada di direktori yang sama dengan script ini.{Colors.ENDC}")
            input(f"\n{Colors.BLUE}📱 Tekan Enter untuk keluar...{Colors.ENDC}")
            break
        
        # Tampilkan daftar file
        show_file_list(files)
        
        # Dapatkan pilihan user
        choice = get_user_choice(len(files))
        
        if choice == 0:
            print(f"\n{Colors.GREEN}👋 Terima kasih telah menggunakan script ini!{Colors.ENDC}")
            break
        elif choice == 'refresh':
            continue
        elif choice == 'help':
            show_help()
            continue
        
        # Proses file yang dipilih
        selected_file = files[choice - 1]['name']
        is_shodan = files[choice - 1]['is_shodan']
        
        print(f"\n{Colors.YELLOW}🎯 File yang dipilih: {selected_file}{Colors.ENDC}")
        if is_shodan:
            print(f"{Colors.GREEN}✅ File terdeteksi sebagai data Shodan{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}⚠️  File mungkin bukan data Shodan standar{Colors.ENDC}")
        
        # Konfirmasi
        confirm = input(f"{Colors.BOLD}📝 Lanjutkan ekstraksi? (y/n): {Colors.ENDC}").strip().lower()
        if confirm not in ['y', 'yes', 'ya']:
            continue
        
        # Generate nama file output
        output_file = generate_output_filename(selected_file)
        
        # Ekstrak data
        success, message = extract_with_progress(selected_file, output_file)
        
        if success:
            show_results_summary(output_file)
        else:
            print(f"\n{Colors.RED}❌ Ekstraksi gagal: {message}{Colors.ENDC}")
        
        # Tanya apakah ingin memproses file lain
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.ENDC}")
        another = input(f"{Colors.BOLD}🔄 Proses file lain? (y/n): {Colors.ENDC}").strip().lower()
        if another not in ['y', 'yes', 'ya']:
            print(f"\n{Colors.GREEN}👋 Terima kasih telah menggunakan script ini!{Colors.ENDC}")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Program dihentikan oleh user. Sampai jumpa!{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error tidak terduga: {e}{Colors.ENDC}")
        print(f"{Colors.YELLOW}💡 Silakan laporkan error ini jika terus terjadi.{Colors.ENDC}")
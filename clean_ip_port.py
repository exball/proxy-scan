#!/usr/bin/env python3

import re
import os

def clean_ip_port_file():
    """
    Membersihkan file untuk hanya menyisakan format IP:Port
    """
    
    print("=" * 50)
    print("🧹 SCRIPT PEMBERSIH IP:PORT")
    print("=" * 50)
    
    # Input nama file
    while True:
        filename = input("Masukkan nama file yang ingin dibersihkan: ").strip()
        
        if not filename:
            print("❌ Nama file tidak boleh kosong!")
            continue
            
        # Jika tidak ada path, gunakan direktori saat ini
        if not os.path.dirname(filename):
            filepath = os.path.join('/home/exball/Tunnel/proxy-scan', filename)
        else:
            filepath = filename
            
        # Cek apakah file ada
        if os.path.exists(filepath):
            break
        else:
            print(f"❌ File '{filepath}' tidak ditemukan!")
            print("💡 Pastikan nama file benar dan file ada di direktori yang tepat")
            continue
    
    # Pattern untuk mencocokkan IP:Port
    ip_port_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+)\b'
    
    try:
        # Baca file asli
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        print(f"📖 Membaca file: {filepath}")
        
        # Cari semua IP:Port dalam file
        ip_ports = re.findall(ip_port_pattern, content)
        
        if not ip_ports:
            print("❌ Tidak ada IP:Port yang ditemukan dalam file!")
            return
        
        # Hapus duplikat sambil menjaga urutan
        unique_ip_ports = []
        seen = set()
        for ip_port in ip_ports:
            if ip_port not in seen:
                unique_ip_ports.append(ip_port)
                seen.add(ip_port)
        
        print(f"🔍 Ditemukan {len(ip_ports)} IP:Port (termasuk duplikat)")
        print(f"✨ Setelah menghapus duplikat: {len(unique_ip_ports)} IP:Port unik")
        
        # Tanya apakah ingin backup file asli
        backup_choice = input("\n💾 Apakah Anda ingin membuat backup file asli? (y/n): ").strip().lower()
        
        if backup_choice in ['y', 'yes', 'ya']:
            backup_filepath = filepath + '.backup'
            with open(backup_filepath, 'w', encoding='utf-8') as backup_file:
                backup_file.write(content)
            print(f"✅ Backup dibuat: {backup_filepath}")
        
        # Tulis kembali file dengan hanya IP:Port
        with open(filepath, 'w', encoding='utf-8') as file:
            for ip_port in unique_ip_ports:
                file.write(ip_port + '\n')
        
        print("\n" + "=" * 50)
        print("✅ FILE BERHASIL DIBERSIHKAN!")
        print("=" * 50)
        print(f"📁 File: {filepath}")
        print(f"📊 Total IP:Port unik: {len(unique_ip_ports)}")
        print("📝 Format file sekarang hanya berisi IP:Port")
        
        # Tampilkan preview beberapa baris pertama
        print("\n📋 Preview 5 baris pertama:")
        print("-" * 30)
        for i, ip_port in enumerate(unique_ip_ports[:5]):
            print(f"{i+1:2d}. {ip_port}")
        
        if len(unique_ip_ports) > 5:
            print(f"    ... dan {len(unique_ip_ports) - 5} baris lainnya")
            
    except Exception as e:
        print(f"❌ Terjadi error: {str(e)}")

def main():
    """
    Fungsi utama dengan opsi untuk menjalankan berulang
    """
    while True:
        try:
            clean_ip_port_file()
            
            # Tanya apakah ingin membersihkan file lain
            another = input("\n🔄 Apakah ingin membersihkan file lain? (y/n): ").strip().lower()
            if another not in ['y', 'yes', 'ya']:
                break
                
            print("\n" + "="*50)
            
        except KeyboardInterrupt:
            print("\n\n👋 Program dihentikan oleh user. Terima kasih!")
            break
        except Exception as e:
            print(f"\n❌ Error tidak terduga: {str(e)}")
            break
    
    print("\n👋 Terima kasih telah menggunakan script ini!")

if __name__ == "__main__":
    main()
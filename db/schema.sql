CREATE DATABASE IF NOT EXISTS uks_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE uks_db;

-- 1. Faskes mitra (dibuat duluan karena dipakai users & rujukan)
CREATE TABLE faskes_mitra (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nama VARCHAR(150) NOT NULL,
  jenis ENUM('Puskesmas','RS') NOT NULL,
  alamat TEXT,
  kontak VARCHAR(50)
);

-- 2. Users
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nama VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('mahasiswa','petugas','admin','mitra') NOT NULL,
  faskes_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (faskes_id) REFERENCES faskes_mitra(id)
);

-- 3. Mahasiswa
CREATE TABLE mahasiswa (
  user_id INT PRIMARY KEY,
  nim VARCHAR(20) NOT NULL UNIQUE,
  prodi VARCHAR(100),
  angkatan YEAR,
  no_hp VARCHAR(20),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 4. Keluhan
CREATE TABLE keluhan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  kode VARCHAR(12) NOT NULL UNIQUE,
  mahasiswa_id INT NOT NULL,
  tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
  keluhan_utama VARCHAR(255) NOT NULL,
  lama_keluhan VARCHAR(50),
  tingkat_nyeri TINYINT CHECK (tingkat_nyeri BETWEEN 0 AND 10),
  gejala_lain TEXT,
  riwayat_alergi TEXT,
  status ENUM('Menunggu','Dilayani','Dirujuk','Selesai') DEFAULT 'Menunggu',
  FOREIGN KEY (mahasiswa_id) REFERENCES mahasiswa(user_id)
);

-- 5. Obat
CREATE TABLE obat (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nama_obat VARCHAR(120) NOT NULL,
  kategori VARCHAR(80),
  satuan VARCHAR(30),
  stok INT NOT NULL DEFAULT 0 CHECK (stok >= 0),
  stok_minimum INT NOT NULL DEFAULT 10
);

-- 6. Obat masuk
CREATE TABLE obat_masuk (
  id INT AUTO_INCREMENT PRIMARY KEY,
  obat_id INT NOT NULL,
  jumlah INT NOT NULL CHECK (jumlah > 0),
  tanggal_masuk DATE NOT NULL,
  tanggal_kadaluarsa DATE,
  dicatat_oleh INT NOT NULL,
  FOREIGN KEY (obat_id) REFERENCES obat(id),
  FOREIGN KEY (dicatat_oleh) REFERENCES users(id)
);

-- 7. Pelayanan
CREATE TABLE pelayanan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  keluhan_id INT NOT NULL,
  petugas_id INT NOT NULL,
  diagnosis_awal VARCHAR(255),
  tindakan TEXT,
  tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (keluhan_id) REFERENCES keluhan(id),
  FOREIGN KEY (petugas_id) REFERENCES users(id)
);

-- 8. Obat yang diberikan saat pelayanan
CREATE TABLE pelayanan_obat (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pelayanan_id INT NOT NULL,
  obat_id INT NOT NULL,
  jumlah INT NOT NULL CHECK (jumlah > 0),
  FOREIGN KEY (pelayanan_id) REFERENCES pelayanan(id),
  FOREIGN KEY (obat_id) REFERENCES obat(id)
);

-- 9. Rujukan
CREATE TABLE rujukan (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pelayanan_id INT NOT NULL,
  faskes_id INT NOT NULL,
  alasan_rujukan TEXT NOT NULL,
  status ENUM('Dibuat','Diterima','Ditangani','Selesai') DEFAULT 'Dibuat',
  catatan_tindak_lanjut TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (pelayanan_id) REFERENCES pelayanan(id),
  FOREIGN KEY (faskes_id) REFERENCES faskes_mitra(id)
);

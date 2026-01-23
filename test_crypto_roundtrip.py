from crypto_engine import encrypt_file, decrypt_file
from pathlib import Path


def main() -> None:
    password = "test-password-123"
    plaintext = ("hello world" * 100).encode("utf-8")

    plain_path = Path("_tmp_plain.txt")
    enc_path = Path("_tmp_plain.txt.enc")
    dec_path = Path("_tmp_plain.dec.txt")

    plain_path.write_bytes(plaintext)
    encrypt_file(str(plain_path), str(enc_path), password)
    decrypt_file(str(enc_path), str(dec_path), password)

    recovered = dec_path.read_bytes()
    print("Round-trip success:", recovered == plaintext)


if __name__ == "__main__":
    main()

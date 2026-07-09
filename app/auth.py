"""Sifre hash'leme yardimcilari.

bcrypt/passlib gibi ek bir bagimlilik EKLEMIYORUZ - Windows'ta bu tur
paketlerin derleme/kurulum sorunlari cikarabildigini bu projede defalarca
gorduk. Bunun yerine Python'un kendi stdlib'indeki hashlib.pbkdf2_hmac
kullaniliyor - hicbir ek paket gerektirmez, kriptografik olarak yeterince
guclu (200.000 iterasyon + rastgele salt)."""
import hashlib
import secrets

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, digest_hex = stored_hash.split("$", 1)
    try:
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    except ValueError:
        return False
    return secrets.compare_digest(check.hex(), digest_hex)

"""Unit tests for crypto module"""

import pytest
from app.core.crypto import CryptoService


@pytest.mark.unit
class TestCryptoService:
    """加密服务测试"""

    def test_encrypt_decrypt_roundtrip(self):
        """测试加密解密往返"""
        crypto = CryptoService("test_pepper")
        plaintext = "13912345678"

        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_encrypt_produces_different_ciphertext(self):
        """测试加密产生不同密文（随机 nonce）"""
        crypto = CryptoService("test_pepper")
        plaintext = "test_value"

        encrypted1 = crypto.encrypt(plaintext)
        encrypted2 = crypto.encrypt(plaintext)

        # 由于使用随机 nonce，密文应该不同
        assert encrypted1 != encrypted2

        # 但解密结果相同
        assert crypto.decrypt(encrypted1) == plaintext
        assert crypto.decrypt(encrypted2) == plaintext

    def test_hash_phone(self):
        """测试手机号哈希"""
        crypto = CryptoService("test_pepper")
        phone = "13912345678"

        hash1 = crypto.hash_phone(phone)
        hash2 = crypto.hash_phone(phone)

        # 同样的手机号产生相同的哈希
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256

    def test_hash_phone_normalizes_format(self):
        """测试手机号哈希格式化"""
        crypto = CryptoService("test_pepper")

        hash1 = crypto.hash_phone("13912345678")
        hash2 = crypto.hash_phone("139 1234 5678")  # 带空格
        hash3 = crypto.hash_phone("139-1234-5678")  # 带破折号

        assert hash1 == hash2 == hash3

    def test_different_peppers_produce_different_results(self):
        """测试不同 pepper 产生不同结果"""
        crypto1 = CryptoService("pepper1")
        crypto2 = CryptoService("pepper2")

        plaintext = "test"

        # 不同 pepper 加密结果不同
        encrypted1 = crypto1.encrypt(plaintext)
        encrypted2 = crypto2.encrypt(plaintext)

        # 不能用另一个 pepper 解密
        with pytest.raises(Exception):
            crypto2.decrypt(encrypted1)

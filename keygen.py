# -*- coding: utf-8 -*-
"""
Setu License Key Generator — Aghanya Devanya Enterprises (vendor only)

Keys are digitally signed (ECDSA P-256). The software only contains the PUBLIC key,
so nobody can create keys without the private key file `setu-license-private.pem`.
Every key is tied to one installation: the client reads its Install ID
(e.g. SETU-7F3K-92QD) from the Setu Sign Up / License screen and sends it to you.

  python keygen.py init                         one time: create the private key (KEEP IT SAFE)
  python keygen.py                              interactive
  python keygen.py <INSTALL-ID> <plan> [hotel]  plan: 1m 2m 3m 6m 1y life demo1h demo24h reset
  python keygen.py verify <KEY> <INSTALL-ID>

Requires: pip install cryptography
"""
import os
import sys
import csv
import base64
import hashlib
import secrets
import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.exceptions import InvalidSignature

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_FILE = os.path.join(BASE_DIR, 'setu-license-private.pem')
ISSUED_CSV = os.path.join(BASE_DIR, 'Activation_Keys', 'Setu_Issued_Keys.csv')
EPOCH = datetime.date(2026, 1, 1)
B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'

# kind: 1 = days, 2 = minutes (demo), 3 = lifetime, 4 = owner password reset (one use, 2 days)
PLANS = {
    '1m':      (1, 30,  '1 Month (30 Days)'),
    '2m':      (1, 60,  '2 Months (60 Days)'),
    '3m':      (1, 90,  '3 Months (90 Days)'),
    '6m':      (1, 180, '6 Months (180 Days)'),
    '1y':      (1, 365, '1 Year (365 Days)'),
    'life':    (3, 0,   'Lifetime'),
    'demo1h':  (2, 60,  'Demo (1 Hour)'),
    'demo24h': (2, 1440, 'Demo (24 Hours)'),
    'reset':   (4, 0,   'Owner Password Reset'),
}


def b32encode(data):
    bits = ''.join(f'{b:08b}' for b in data)
    bits += '0' * (-len(bits) % 5)
    return ''.join(B32[int(bits[i:i + 5], 2)] for i in range(0, len(bits), 5))


def b32decode(text, nbytes):
    bits = ''.join(f'{B32.index(c):05b}' for c in text)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, nbytes * 8, 8))


def clean_install_id(install_id):
    return ''.join(c for c in install_id.upper() if c.isalnum())


def install_hash(install_id):
    return hashlib.sha256(clean_install_id(install_id).encode('ascii')).digest()[:4]


def load_private_key():
    if not os.path.exists(PRIVATE_KEY_FILE):
        sys.exit('Private key not found. Run first: python keygen.py init')
    with open(PRIVATE_KEY_FILE, 'rb') as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def public_key_b64(priv):
    raw = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.b64encode(raw).decode('ascii')


def make_key(install_id, plan):
    kind, value, _ = PLANS[plan]
    issued = (datetime.date.today() - EPOCH).days
    payload = bytes([1, kind]) + value.to_bytes(2, 'big') + install_hash(install_id) + secrets.token_bytes(3) + issued.to_bytes(2, 'big')
    der = load_private_key().sign(payload, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    sig = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
    body = b32encode(payload + sig)
    return 'SETU-' + '-'.join(body[i:i + 8] for i in range(0, len(body), 8))


def verify_key(key, install_id):
    text = ''.join(c for c in key.upper() if c in B32)
    if not text.startswith('SETU'):
        return None
    raw = b32decode(text[4:], 77)
    payload, sig = raw[:13], raw[13:]
    pub = load_private_key().public_key()
    try:
        pub.verify(encode_dss_signature(int.from_bytes(sig[:32], 'big'), int.from_bytes(sig[32:], 'big')), payload, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        return None
    if payload[4:8] != install_hash(install_id):
        return None
    return {'kind': payload[1], 'value': int.from_bytes(payload[2:4], 'big')}


def log_key(install_id, plan, hotel, key):
    os.makedirs(os.path.dirname(ISSUED_CSV), exist_ok=True)
    new = not os.path.exists(ISSUED_CSV)
    with open(ISSUED_CSV, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['Date', 'Hotel', 'Install_ID', 'Plan', 'Key'])
        w.writerow([datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), hotel, install_id, PLANS[plan][2], key])


def cmd_init():
    if os.path.exists(PRIVATE_KEY_FILE):
        sys.exit('A private key already exists. Do not create a new one, or all previously issued keys will stop working.')
    priv = ec.generate_private_key(ec.SECP256R1())
    with open(PRIVATE_KEY_FILE, 'wb') as f:
        f.write(priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    print('Private key created:', PRIVATE_KEY_FILE)
    print('Back up this file to a pen drive / Google Drive. Never share it and never upload it to GitHub.')
    print('\nSet LIC_PUBKEY in hotel_erp.html to:\n' + public_key_b64(priv))


def main():
    args = sys.argv[1:]
    if args[:1] == ['init']:
        return cmd_init()
    if args[:1] == ['pubkey']:
        return print(public_key_b64(load_private_key()))
    if args[:1] == ['verify'] and len(args) >= 3:
        r = verify_key(args[1], args[2])
        return print('VALID' if r else 'INVALID', r or '')

    print('=' * 64)
    print('   SETU LICENSE KEY GENERATOR — Aghanya Devanya Enterprises')
    print('=' * 64)
    install_id = args[0] if args else input('Client Install ID (e.g. SETU-7F3K-92QD): ').strip()
    if len(clean_install_id(install_id)) < 8:
        sys.exit('Invalid Install ID')
    print('Plans: ' + ', '.join(f'{k} = {v[2]}' for k, v in PLANS.items()))
    plan = args[1] if len(args) > 1 else (input('Plan (Default 1m): ').strip().lower() or '1m')
    if plan not in PLANS:
        sys.exit('Invalid plan')
    hotel = args[2] if len(args) > 2 else input('Hotel name (optional): ').strip()

    key = make_key(install_id, plan)
    log_key(install_id, plan, hotel, key)
    print('\n' + '*' * 64)
    print(f'  {PLANS[plan][2]} — {hotel or install_id}')
    print('  Send this complete key to the client (copy-paste):\n')
    print(key)
    print('*' * 64)
    print('Record saved:', ISSUED_CSV)


if __name__ == '__main__':
    main()

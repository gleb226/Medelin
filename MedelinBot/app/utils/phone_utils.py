
import re

def normalize_phone(phone: str) -> str:

    digits = re.sub('\\D', '', phone or '')

    if digits.startswith('380') and len(digits) == 12:

        return digits

    if digits.startswith('80') and len(digits) == 11:

        return '3' + digits

    if digits.startswith('0') and len(digits) == 10:

        return '38' + digits

    return digits

def format_phone(phone: str) -> str:

    digits = normalize_phone(phone)

    if not digits:

        return ''

    if len(digits) == 12 and digits.startswith('380'):

        return f'+{digits[:2]} ({digits[2:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}'

    return f'+{digits}'

def is_same_phone(phone_a: str, phone_b: str) -> bool:

    return normalize_phone(phone_a) == normalize_phone(phone_b)

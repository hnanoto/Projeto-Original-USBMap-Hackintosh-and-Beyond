# utils_translation.py
import locale
from translations import TRANSLATIONS

def get_system_language():
    try:
        lang, encoding = locale.getlocale()
        if lang:
            return lang.split("_")[0]  # Extrai o código do idioma (ex: "en", "pt", "es")
        else:
            return "en"  # Inglês como padrão se não for possível detectar
    except:
        return "en"

def translate(message, language="en"):
    if message in TRANSLATIONS and language in TRANSLATIONS[message]:
        return TRANSLATIONS[message][language]
    else:
        return message  # Retorna a mensagem original se não houver tradução

def translated_output(func):
    def wrapper(*args, **kwargs):
        language = get_system_language()
        original_output = func(*args, **kwargs)
        if isinstance(original_output, str):
            return translate(original_output, language)
        elif isinstance(original_output, list):
            return [translate(line, language) if isinstance(line, str) else line for line in original_output]
        return original_output
    return wrapper
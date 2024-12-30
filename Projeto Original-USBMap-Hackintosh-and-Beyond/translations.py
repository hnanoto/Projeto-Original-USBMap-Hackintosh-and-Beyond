# translations.py
import locale

TRANSLATIONS = {
    "USBMap": {
        "pt": "USBMap (PT)",
        "es": "USBMap (ES)",
        "fr": "USBMap (FR)"
    },
    "Discover Ports": {
        "pt": "Descobrir Portas",
        "es": "Descubrir Puertos",
        "fr": "Découvrir les Ports"
    },
    "Press [enter] to continue...": {
        "pt": "Pressione [enter] para continuar...",
        "es": "Presione [enter] para continuar...",
        "fr": "Appuyez sur [enter] pour continuer..."
    },
    "Current Controllers:": {
        "pt": "Controladores Atuais:",
        "es": "Controladores Actuales:",
        "fr": "Contrôleurs Actuels:"
    },
    "Erro ao obter a versão do build do macOS: {e}": {
        "pt": "Erro ao obter a versão do build do macOS: {e}",
        "es": "Error al obtener la versión de compilación de macOS: {e}",
        "fr": "Erreur lors de l'obtention de la version de construction de macOS: {e}"
    },
    # Adicione aqui TODAS as mensagens que aparecem no script, em todos os idiomas que quiser suportar
}

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
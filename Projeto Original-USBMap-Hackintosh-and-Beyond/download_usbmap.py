import os
import requests
import zipfile
from io import BytesIO
import shutil
import sys

def download_and_extract_usbmap(destination_dir, force=False):
    """
    Baixa a versão mais recente do USBMap do GitHub, extrai,
    copia o USBMap.py modificado e os arquivos complementares para a pasta extraída.

    Args:
        destination_dir: O diretório onde o USBMap será extraído.
        force: Se True, sempre baixa e extrai, mesmo que a pasta já exista.
    """
    github_repo_url = "https://github.com/corpnewt/USBMap/archive/master.zip"  # URL do zip do repositório
    usbmap_dir = os.path.join(destination_dir, "USBMap-master")  # Nome da pasta após extrair
    script_dir = os.path.dirname(os.path.realpath(__file__))  # Diretório do script atual

    # Caminho do seu USBMap.py modificado (ajuste se necessário)
    source_usbmap_py = os.path.join(script_dir, "USBMap.py")

    # Lista dos arquivos complementares para copiar (sem baixar do GitHub)
    files_to_copy = [
        "menu.py",
        "melhorias.py",
        "translations.py",
        "utils_translation.py",
        "Scripts/utils.py",
        "Scripts/run.py",
        "Scripts/ioreg.py",
        "Scripts/plist.py",
        "Scripts/reveal.py"
    ]

    if os.path.exists(usbmap_dir) and not force:
        print("Pasta USBMap-master já existe. Ignorando download.")
        # Copia o USBMap.py modificado para a pasta existente (substituindo)
        try:
            shutil.copy2(source_usbmap_py, os.path.join(usbmap_dir, "USBMap.py"))
            print(f"Arquivo 'USBMap.py' atualizado em '{usbmap_dir}'")
            return
        except Exception as e:
            print(f"Erro ao atualizar 'USBMap.py': {e}")
            return

    print("Baixando USBMap do GitHub...")
    try:
        response = requests.get(github_repo_url, stream=True)
        response.raise_for_status()
        z = zipfile.ZipFile(BytesIO(response.content))
        z.extractall(destination_dir)
        print("USBMap baixado e extraído com sucesso!")

        # Copiar o USBMap.py modificado para a pasta extraída (substituindo o original)
        shutil.copy2(source_usbmap_py, os.path.join(usbmap_dir, "USBMap.py"))
        print(f"Arquivo 'USBMap.py' atualizado em '{usbmap_dir}'")

        # Copiar os arquivos complementares para a pasta do USBMap
        for filename in files_to_copy:
            src_path = os.path.join(script_dir, filename)
            dest_path = os.path.join(usbmap_dir, filename)
            if os.path.exists(src_path):
                # Cria diretórios de destino se necessário
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(src_path, dest_path)
                print(f"Copiado '{filename}' para '{dest_path}'")
            else:
                print(f"Aviso: Arquivo '{filename}' não encontrado. Não foi possível copiar.")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar USBMap: {e}")
    except Exception as e:
        print(f"Erro ao extrair ou atualizar USBMap: {e}")

if __name__ == "__main__":
    # Verifica se um diretório de destino foi fornecido como argumento
    if len(sys.argv) > 1:
        destination_dir = sys.argv[1]
    else:
        destination_dir = os.getcwd()  # Usa o diretório atual se nenhum for fornecido

    # Verifica se o usuário deseja forçar o download
    force_download = "--force-download" in sys.argv

    download_and_extract_usbmap(destination_dir, force=force_download)
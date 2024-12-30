# download_usbmap.py
import os
import requests  # Importe o módulo requests aqui
import zipfile
from io import BytesIO
import sys

def download_and_extract_usbmap(destination_dir, force=False):
    """
    Baixa a versão mais recente do USBMap do GitHub e extrai para o diretório especificado.

    Args:
        destination_dir: O diretório onde o USBMap será extraído.
        force: Se True, sempre baixa e extrai, mesmo que a pasta já exista.
    """
    github_repo_url = "https://github.com/corpnewt/USBMap/archive/master.zip"  # URL do zip do repositório
    usbmap_dir = os.path.join(destination_dir, "USBMap-master")  # Nome da pasta após extrair

    if os.path.exists(usbmap_dir) and not force:
        print("Pasta USBMap-master já existe. Ignorando download.")
        return

    print("Baixando USBMap do GitHub...")
    try:
        response = requests.get(github_repo_url, stream=True)
        response.raise_for_status()
        z = zipfile.ZipFile(BytesIO(response.content))
        z.extractall(destination_dir)
        print("USBMap baixado e extraído com sucesso!")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar USBMap: {e}")
    except Exception as e:
        print(f"Erro ao extrair USBMap: {e}")

if __name__ == "__main__":
    # Verifica se um diretório de destino foi fornecido como argumento
    if len(sys.argv) > 1:
        destination_dir = sys.argv[1]
    else:
        destination_dir = os.getcwd()  # Usa o diretório atual se nenhum for fornecido

    # Verifica se o usuário deseja forçar o download
    force_download = "--force-download" in sys.argv

    download_and_extract_usbmap(destination_dir, force=force_download)
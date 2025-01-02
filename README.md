# Projeto-Original-USBMap-Hackintosh-and-Beyond
Tutorial: Baixando e Configurando o USBMap Modificado

www.youtube.com/@HackintoshAndBeyond
discord.gg/5hvZ5u7QXQ

Este tutorial explica como usar o script download_usbmap.py para baixar e configurar a versão mais recente do USBMap, uma ferramenta para mapeamento de portas USB em hackintoshes, junto com arquivos complementares que aprimoram sua funcionalidade e traduzem a interface para diferentes idiomas.

Introdução:

O USBMap é uma ferramenta poderosa criada por CorpNewt para auxiliar no complexo processo de mapeamento de portas USB em sistemas hackintosh. Este tutorial se concentra em uma versão modificada do USBMap.py original, complementada por arquivos adicionais que fornecem traduções, melhorias e uma interface de menu aprimorada. Esses arquivos complementares incluem:

menu.py: Responsável por exibir o menu principal traduzido.
melhorias.py: Contém funções que aprimoram o script original e centralizam a lógica para aplicar essas melhorias.
translations.py: Um dicionário com as traduções das mensagens do script para diferentes idiomas.
utils_translation.py: Funções auxiliares para a tradução, incluindo get_system_language e translate.
O que este script (download_usbmap.py) faz:

Baixa a versão mais recente do USBMap: Ele baixa o arquivo master.zip diretamente do repositório oficial do USBMap no GitHub: https://github.com/corpnewt/USBMap.
Extrai o USBMap: Descompacta o arquivo baixado em uma pasta chamada USBMap-master.
Substitui o USBMap.py original: Copia o seu arquivo USBMap.py modificado para a pasta USBMap-master, sobrescrevendo o original.
Copia os arquivos complementares: Copia os arquivos menu.py, melhorias.py, translations.py e utils_translation.py para a pasta USBMap-master, juntamente com os arquivos do USBMap original.
Pré-requisitos:

Python 3: Certifique-se de ter o Python 3 instalado em seu sistema. Você pode verificar a versão digitando python3 --version no terminal.
Biblioteca requests: O script usa a biblioteca requests para fazer downloads. Se você não a tiver instalada, execute o seguinte comando no terminal:
pip3 install requests

Como usar o download_usbmap.py:

Baixe os arquivos: Baixe os seguintes arquivos e coloque-os em uma mesma pasta:
download_usbmap.py
USBMap.py (seu script modificado)
menu.py
melhorias.py
translations.py
utils_translation.py
Scripts/utils.py
Scripts/run.py
Scripts/ioreg.py
Scripts/plist.py
Scripts/reveal.py
Abra o terminal e navegue até a pasta onde você colocou os arquivos:
cd /caminho/para/a/pasta

Execute o script download_usbmap.py:
Para baixar o USBMap na pasta atual:
python3 download_usbmap.py

Para baixar o USBMap em uma pasta específica (por exemplo, na Área de Trabalho):
python3 download_usbmap.py /Users/seu_usuario/Desktop

Para forçar o download e sobrescrever a pasta USBMap-master existente:
python3 download_usbmap.py --force-download

O script fará o seguinte:
Baixará o arquivo master.zip do repositório oficial do USBMap.
Extrairá o conteúdo para uma pasta chamada USBMap-master.
Substituirá o arquivo USBMap.py original pelo seu USBMap.py modificado.
Copiará os arquivos menu.py, melhorias.py, translations.py e utils_translation.py para a pasta USBMap-master.
Após a conclusão bem-sucedida, você terá a seguinte estrutura:
/caminho/para/a/pasta/
├── download_usbmap.py
└── USBMap-master/
    ├── USBMap.py (seu script modificado)
    ├── menu.py
    ├── melhorias.py
    ├── translations.py
    ├── utils_translation.py
    ├── Scripts/
    │   ├── utils.py
    │   ├── run.py
    │   ├── ioreg.py
    │   ├── plist.py
    │   └── reveal.py
    └── ... (outros arquivos originais do USBMap) ...

    Navegue até a pasta USBMap-master:
cd /caminho/para/a/pasta/USBMap-master/

Execute o script USBMap.py modificado:
python3 USBMap.py

O script USBMap.py agora será executado, e o menu inicial deve aparecer traduzido para o idioma do seu sistema (se houver uma tradução disponível no translations.py).
Explicação do código download_usbmap.py:

import os
import requests
import zipfile
from io import BytesIO
import shutil
import sys

def download_and_extract_usbmap(destination_dir, force=False):
    # ... (Esta função faz o download, extração e cópia dos arquivos, como explicado anteriormente) ...

if __name__ == "__main__":
    # Verifica se um diretório de destino foi fornecido como argumento
    if len(sys.argv) > 1:
        destination_dir = sys.argv[1]
    else:
        destination_dir = os.getcwd()  # Usa o diretório atual se nenhum for fornecido

    # Verifica se o usuário deseja forçar o download
    force_download = "--force-download" in sys.argv

    download_and_extract_usbmap(destination_dir, force=force_download)

    import: Importa os módulos necessários:
os: Para manipulação de arquivos e diretórios.
requests: Para fazer requisições HTTP (baixar o zip).
zipfile: Para lidar com arquivos zip.
io.BytesIO: Para lidar com o arquivo zip na memória.
shutil: Para copiar arquivos.
sys: Para acessar argumentos da linha de comando.
download_and_extract_usbmap(destination_dir, force=False):
github_repo_url: URL do repositório oficial do USBMap.
usbmap_dir: Caminho completo para a pasta USBMap-master.
script_dir: Caminho completo para a pasta onde o script download_usbmap.py está sendo executado.
source_usbmap_py: Caminho completo para o seu USBMap.py modificado.
files_to_copy: Lista de arquivos complementares que serão copiados.
Verifica se a pasta USBMap-master já existe e se o parâmetro force é False. Se sim, pula o download e apenas copia o USBMap.py modificado, se não houver erros.
Faz o download do master.zip do GitHub usando requests.get().
Extrai o conteúdo do zip para destination_dir usando zipfile.ZipFile.
Copia o seu USBMap.py modificado para dentro da pasta USBMap-master, substituindo o original.
Copia os arquivos complementares (menu.py, melhorias.py, etc.) para a pasta USBMap-master.
Trata exceções requests.exceptions.RequestException e Exception para lidar com erros de download ou extração.
if __name__ == "__main__"::
Verifica se o script está sendo executado como o programa principal.
Obtém o diretório de destino a partir dos argumentos de linha de comando (sys.argv) ou usa o diretório atual (os.getcwd()) como padrão.
Verifica se a flag --force-download foi fornecida para forçar o download.
Chama a função download_and_extract_usbmap() para realizar o download e a configuração.
Agradecimentos:

Este script e suas melhorias são baseados no excelente trabalho original de CorpNewt, que desenvolveu o USBMap e o disponibilizou publicamente. A ele, nossos sinceros agradecimentos!

Considerações Importantes:

Mantenha os arquivos complementares atualizados: Sempre que você modificar um dos arquivos complementares (menu.py, melhorias.py, translations.py, utils_translation.py), lembre-se de atualizar também os arquivos correspondentes na pasta USBMap-master para que as alterações tenham efeito.
Teste em diferentes ambientes: Teste o script em diferentes sistemas e versões do Python para garantir a compatibilidade.

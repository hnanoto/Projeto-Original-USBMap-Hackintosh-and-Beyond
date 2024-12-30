# Projeto-Original-USBMap-Hackintosh-and-Beyond
Tutorial: Baixando e Configurando o USBMap Modificado

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

# melhorias.py
import subprocess
import os
import re
import plistlib
import binascii
from utils_translation import translate, get_system_language
from melhorias import apply_enhancements, get_os_build_version, hex_to_data_safe, check_and_build, build_info_plist
from collections import OrderedDict
def get_os_build_version(language="en"):
    # Obtém a versão do build do macOS, tratando erros de forma mais específica.
    try:
        process = subprocess.run(['sw_vers', '-buildVersion'], capture_output=True, text=True, check=True)
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(translate(f"Erro ao executar 'sw_vers -buildVersion': {e.returncode} - {e.stderr}", language))
        return "Unknown"
    except FileNotFoundError:
        print(translate("Erro: Comando 'sw_vers' não encontrado. Verifique sua instalação do macOS.", language))
        return "Unknown"
    except Exception as e:
        print(translate(f"Erro inesperado ao obter a versão do build do macOS: {e}", language))
        return "Unknown"

def clear_screen():
    """Limpa a tela do terminal."""
    os.system("cls" if os.name == "nt" else "clear")

def hex_to_data_safe(value):
    """Converte uma string hexadecimal em bytes, lidando com diferentes versões do Python."""
    try:
        # Tenta usar plistlib.UUID (disponível a partir do Python 3.9)
        return plistlib.UUID(binascii.unhexlify(check_hex(value).encode("utf-8")))
    except AttributeError:
        # Se plistlib.UUID não estiver disponível, usa binascii.unhexlify
        return binascii.unhexlify(check_hex(value).encode("utf-8"))

def check_hex(value):
    """Remove caracteres não hexadecimais da string."""
    return re.sub(r"[^0-9A-Fa-f]+", "", value.lower().replace("0x", ""))

def check_and_build(
    self,
    kext_path,
    info_path,
    skip_empty=True,
    legacy=False,
    skip_disabled=False,
    padded_to=0,
    force_matching=None,
    ):
    info_plist = self.build_info_plist(
        skip_empty=skip_empty,
        legacy=legacy,
        skip_disabled=skip_disabled,
        padded_to=padded_to,
        force_matching=force_matching,
    )
    if os.path.exists(kext_path):
        print(
            f"Localizado {os.path.basename(kext_path)} existente - removendo..."
        )
        shutil.rmtree(kext_path, ignore_errors=True)
    print("Criando estrutura de pacote...")
    os.makedirs(os.path.join(kext_path, "Contents"))
    print("Escrevendo Info.plist...")
    with open(info_path, "wb") as f:
        plistlib.dump(info_plist, f, sort_keys=False)

def build_info_plist(self, skip_empty=True, legacy=False, skip_disabled=False, padded_to=0, force_matching=None):
    output_plist = {
        "CFBundleDevelopmentRegion": "English",
        "CFBundleGetInfoString": "v1.0",
        "CFBundleIdentifier": "com.corpnewt.USBMap",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "USBMap",
        "CFBundlePackageType": "KEXT",
        "CFBundleShortVersionString": "1.0",
        "CFBundleSignature": "????",
        "CFBundleVersion": "1.0",
        "IOKitPersonalities": {},
        "OSBundleRequired": "Root",
    }
    for x in self.merged_list:
        if padded_to > 0:
            padded_to = 30 if padded_to > 30 else padded_to
            ports = {}
            original_ports = self.merged_list[x]["ports"]
            for a in range(padded_to):
                addr = self.hex_swap(hex(a + 1)[2:].rjust(8, "0"))
                ports[addr] = {
                    "type": "Unknown",
                    "port": addr,
                    "enabled": True,
                }
                if original_ports.get(addr, {}).get("contains_hub"):
                    ports[addr]["contains_hub"] = True
        else:
            ports = self.merged_list[x]["ports"]
        if (
            all((ports[y].get("enabled", False) == False for y in ports))
            and skip_empty
        ):
            continue
        top_port = hs_port = ss_port = uk_port = 0
        top_data = self.hex_to_data("00000000")
        new_entry = {
            "CFBundleIdentifier": "com.apple.driver.AppleUSBMergeNub"
            if legacy
            else "com.apple.driver.AppleUSBHostMergeProperties",
            "IOClass": "AppleUSBMergeNub"
            if legacy
            else "AppleUSBHostMergeProperties",
            "IONameMatch": self.merged_list[x].get("parent_name"),
            "IOPathMatch": self.merged_list[x].get("ioservice_path"),
            "IOParentMatch": {
                "IOPropertyMatch": {
                    "pcidebug": self.merged_list[x].get("pci_debug")
                }
            },
            "IOProviderClass": self.merged_list[x]["type"],
            "IOProviderMergeProperties": {
                "kUSBMuxEnabled": False,
                "port-count": 0,
                "ports": OrderedDict(),
            },
            "model": self.smbios,
        }
        pop_keys = ("IONameMatch", "locationID", "IOPathMatch", "IOParentMatch")
        save_key = "IONameMatch"
        if "locationid" in self.merged_list[x]:
            new_entry["locationID"] = self.merged_list[x]["locationid"]
            new_entry["IOProviderClass"] = "AppleUSB20InternalHub"
            new_entry["IOProbeScore"] = 5000
            save_key = "locationID"
        elif force_matching and force_matching in pop_keys:
            save_key = force_matching
        elif "pci_debug" in self.merged_list[x]:
            save_key = "IOParentMatch"
        elif "ioservice_path" in self.merged_list[x]:
            save_key = "IOPathMatch"
        for key in pop_keys:
            if key == save_key:
                continue
            new_entry.pop(key, None)
        if "XHCI" in self.merged_list[x]["type"]:
            new_entry["IOProviderMergeProperties"]["kUSBMuxEnabled"] = True
        for port_num in sorted(ports):
            port = ports[port_num]
            if port["type"] == "Unknown":
                uk_port += 1
                port_name = self.get_numbered_name("UK00", uk_port, False)
            elif "USB3" in port["type"]:
                ss_port += 1
                port_name = self.get_numbered_name("SS00", ss_port, False)
            else:
                hs_port += 1
                port_name = self.get_numbered_name(
                    "HS00"
                    if "XHCI" in self.merged_list[x]["type"]
                    else "PRT0",
                    hs_port,
                    False,
                )
            if not port.get("enabled", False) and skip_disabled:
                continue
            port_number = self.hex_dec(self.hex_swap(port["port"]))
            if port.get("enabled") and port_number > top_port:
                top_port = port_number
                top_data = self.hex_to_data(port["port"])
            usb_connector = port.get(
                "type_override",
                255
                if port.get("contains_hub")
                else port.get("connector", -1),
            )
            if usb_connector == -1:
                usb_connector = (
                    3 if "XHCI" in self.merged_list[x]["type"] else 0
                )
            new_entry["IOProviderMergeProperties"]["ports"][port_name] = {
                "UsbConnector": usb_connector,
                "port" if port.get("enabled") else "#port": self.hex_to_data(
                    port["port"]
                ),
            }
            if "comment" in port:
                new_entry["IOProviderMergeProperties"]["ports"][port_name][
                    "Comment"
                ] = port["comment"]
        new_entry["IOProviderMergeProperties"]["port-count"] = top_data
        entry_name = self.smbios + "-" + x.split("@")[0]
        entry_num = 0
        while True:
            test_name = entry_name
            if entry_num > 0:
                test_name += f"-{entry_num}"
            if test_name not in output_plist["IOKitPersonalities"]:
                entry_name = test_name
                break
            entry_num += 1
        output_plist["IOKitPersonalities"][entry_name] = new_entry
        return output_plist
    
def apply_enhancements(usbmap_instance):
    """Aplica as melhorias ao script USBMap.

    Args:
        usbmap_instance: Uma instância da classe USBMap.
    """
    language = get_system_language()

    # 1. Tradução (agora usando a função `translate` do `utils_translation.py`)
    usbmap_instance.u.head(translate("USBMap", language)) # Traduz o cabeçalho na função main
    # ... Tradução de outras mensagens em main()

    # 2. Melhorias na função get_os_build_version
    usbmap_instance.get_os_build_version = lambda: get_os_build_version(language)

    # 3. Força a utilização da hex_to_data_safe
    usbmap_instance.hex_to_data = hex_to_data_safe

    # 4. Limpeza de tela antes do menu (chamada em `main()` para afetar a exibição do menu)
    clear_screen()

    # 5. Outras melhorias podem ser adicionadas aqui, se necessário
    # Exemplo: usbmap_instance.alguma_funcao = lambda x: outra_funcao_de_melhoria(x, language)
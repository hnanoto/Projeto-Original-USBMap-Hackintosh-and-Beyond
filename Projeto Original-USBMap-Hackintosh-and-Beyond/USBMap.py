import os, sys, re, json, binascii, shutil
from Scripts import run, utils, ioreg, plist, reveal
from collections import OrderedDict
from datetime import datetime
import subprocess
from datetime import datetime
import plistlib
from utils_translation import get_system_language, translate, translated_output
from menu import display_main_menu


def translated_output(func):
    def wrapper(*args, **kwargs):
        language = get_system_language()
        if 'translate_text' in kwargs:
            translate_text = kwargs.pop('translate_text')
        else:
            translate_text = True
        
        original_output = func(*args, **kwargs)
        
        if translate_text:
            if isinstance(original_output, str):
                return translate(original_output, language)
            elif isinstance(original_output, list):
                return [translate(line, language) if isinstance(line, str) else line for line in original_output]
        return original_output
    return wrapper
class USBMap:
    def __init__(self):
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        self.u = utils.Utils("USBMap")
        # Verify running os
        if not sys.platform.lower() == "darwin":
            self.u.head("Wrong OS!")
            print("")
            print("USBMap can only be run on macOS!")
            print("")
            self.u.grab("Press [enter] to exit...")
            exit()
        self.r = run.Run()
        self.i = ioreg.IOReg()
        self.re = reveal.Reveal()
        self.map_hubs = True # Enable to show hub ports/devices in mapping
        self.controllers = None
        self.smbios = None
        self.os_build_version = "Unknown"
        self.os_version = "0.0.0"
USB_PORT_REGEX = re.compile(r"Apple[a-zA-Z0-9]*USB\d*[A-Z]+Port,")
USB_CONT_REGEX = re.compile(r"Apple[a-zA-Z0-9]*USB[0-9A-Z]+,")
USB_HUB_REGEX = re.compile(r"Apple[a-zA-Z0-9]*USB\d+[a-zA-Z]*Hub,")
USB_HUBP_REGEX = re.compile(r"Apple[a-zA-Z0-9]*USB\d+[a-zA-Z]*HubPort,")
USB_EXT_REGEX = [
    re.compile(r"<class [a-zA-Z0-9]*BluetoothHostControllerUSBTransport,"),
    re.compile(r"^(?!.*IOUSBHostDevice@).*<class IOUSBHostDevice,")
]
IOKIT_PERSONALITIES = "IOKitPersonalities"
MODEL = "model"
IONAMEMATCH = "IONameMatch"
USB_TYPES = {
    0: "Type A connector",
    1: "Mini-AB connector",
    2: "ExpressCard",
    3: "USB 3 Standard-A connector",
    4: "USB 3 Standard-B connector",
    5: "USB 3 Micro-B connector",
    6: "USB 3 Micro-AB connector",
    7: "USB 3 Power-B connector",
    8: "Type C connector - USB2-only",
    9: "Type C connector - USB2 and SS with Switch",
    10: "Type C connector - USB2 and SS without Switch",
    255: "Proprietary connector",
}
IOREG_DUMP_PATH = "ioreg.txt"
SYSTEM_PROFILER_DUMP_PATH = "system_profiler.txt"
def get_python_version():
    return sys.version_info[:2]  # Retorna uma tupla (major, minor)

def is_python_version_compatible():
    version = get_python_version()
    if version < (3, 0):
        print("Este script requer Python 3 ou superior.")
        return False
    return True

class USBMap:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        os.chdir(self.script_dir)
        self.u = utils.Utils("USBMap")
        self.r = run.Run()
        self.i = ioreg.IOReg()
        self.re = reveal.Reveal()
        self.load_constants()
        self.ioreg = self.populate_ioreg()
        self.local_ioreg = False
        self.by_ioreg = None
        self.merged_list = self.load_usb_list()
        self.connected_controllers = self.check_controllers()
        self.all_addrs = []
        self.illegal_names = self.get_illegal_names()

    def load_constants(self):
        # --- Configurações ---
        self.map_hubs = True
        self.controllers = None
        self.smbios = None
        self.os_build_version = self.get_os_build_version()
        self.os_version = self.get_os_version()
        self.discover_wait = 5
        self.default_names = ("XHC1", "EHC1", "EHC2")
        self.cs = "\u001b[32;1m"
        self.ce = "\u001b[0m"
        self.bs = "\u001b[36;1m"
        self.rs = "\u001b[31;1m"
        self.nm = "\u001b[35;1m"
        self.usb_list = os.path.join(self.script_dir, "Scripts", "USB.plist")
        self.output = os.path.join(self.script_dir, "Results")
        self.ssdt_path = os.path.join(self.output, "SSDT-USB-Reset.dsl")
        self.rsdt_path = os.path.join(self.output, "SSDT-RHUB-Reset.dsl")
        self.kext_path = os.path.join(self.output, "USBMap.kext")
        self.info_path = os.path.join(self.kext_path, "Contents", "Info.plist")
        self.legacy_kext_path = os.path.join(self.output, "USBMapLegacy.kext")
        self.legacy_info_path = os.path.join(self.legacy_kext_path, "Contents", "Info.plist")
        self.dummy_kext_path = os.path.join(self.output, "USBMapDummy.kext")
        self.dummy_info_path = os.path.join(self.dummy_kext_path, "Contents", "Info.plist")
        self.dummy_legacy_kext_path = os.path.join(self.output, "USBMapLegacyDummy.kext")
        self.dummy_legacy_info_path = os.path.join(self.dummy_legacy_kext_path, "Contents", "Info.plist")
        self.oc_patches = os.path.join(self.output, "patches_OC.plist")
        self.clover_patches = os.path.join(self.output, "patches_Clover.plist")
        self.plugin_path = "/System/Library/Extensions/IOUSBHostFamily.kext/Contents/PlugIns"

    def get_os_build_version(self):
        # Obtém a versão do build do macOS
        try:
            process = subprocess.run(['sw_vers', '-buildVersion'], capture_output=True, text=True)
            return process.stdout.strip()
        except Exception as e:
            print(f"Erro ao obter a versão do build do macOS: {e}")
            return "Unknown"

    def get_os_version(self):
        # Obtém a versão do produto do macOS
        try:
            process = subprocess.run(['sw_vers', '-productVersion'], capture_output=True, text=True)
            return process.stdout.strip()
        except Exception as e:
            print(f"Erro ao obter a versão do produto do macOS: {e}")
            return "0.0.0"

    def check_macos_version(self):
        # Verifica se a versão do macOS é suportada
        if not self.os_version or self.os_version == "0.0.0":
            self.u.head("Erro de detecção do macOS!")
            print("Não foi possível determinar a versão do macOS.")
            print("O script pode não funcionar como esperado.")
            self.u.grab("Pressione [enter] para continuar...")
            return

        os_major, os_minor, _ = self.os_version.split(".")

        if int(os_major) < 10 or (int(os_major) == 10 and int(os_minor) < 14):
            self.u.head("Versão do macOS não suportada!")
            print(f"Versão detectada do macOS: {self.os_version}")
            print("Este script é projetado para macOS Mojave (10.14) e mais recente.")
            self.u.grab("Pressione [enter] para sair...")
            exit()

        print(f"Versão do macOS detectada: {self.os_version}")

    def load_usb_list(self):
        # Carrega a lista USB existente ou retorna um dicionário vazio
        try:
            if os.path.exists(self.usb_list):
                with open(self.usb_list, "rb") as f:
                    return plistlib.load(f, dict_type=OrderedDict)
        except Exception as e:
            print(f"Erro ao carregar {self.usb_list}: {e}")
        return OrderedDict()

    def get_illegal_names(self):
        # Obtém nomes ilegais com base no SMBIOS e nos plugins do IOUSBHostFamily
        if not self.smbios or not os.path.exists(self.plugin_path):
            return list(self.default_names)
        illegal_names = []
        try:
            for plugin in os.listdir(self.plugin_path):
                plug_path = os.path.join(self.plugin_path, plugin)
                info_path = os.path.join(plug_path, "Contents", "Info.plist")
                if plugin.startswith(".") or not os.path.isdir(plug_path) or not os.path.exists(info_path):
                    continue
                with open(info_path, "rb") as f:
                    plist_data = plistlib.load(f)
                    for key in plist_data:
                        if not key.startswith(IOKIT_PERSONALITIES):
                            continue
                        walk_dict = plist_data[key]
                        for k in walk_dict:
                            smbios_entry = walk_dict[k]
                            if not all((x in smbios_entry for x in (MODEL, IONAMEMATCH))):
                                continue
                            if smbios_entry[MODEL] == self.smbios:
                                illegal_names.append(smbios_entry[IONAMEMATCH])
        except Exception as e:
            print(f"Erro ao obter nomes ilegais: {e}")
        return sorted(list(set(illegal_names)))

    def get_map_list(self):
        # Obtém uma lista de padrões de regex para corresponder a controladores USB, portas e dispositivos
        map_list = [USB_CONT_REGEX, USB_PORT_REGEX, USB_HUB_REGEX] + USB_EXT_REGEX
        if self.map_hubs:
            map_list.append(USB_HUBP_REGEX)
        return map_list

    def get_port_map_list(self):
        # Obtém uma lista de padrões de regex para corresponder a portas USB
        map_list = [USB_PORT_REGEX]
        if self.map_hubs:
            map_list.append(USB_HUBP_REGEX)
        return map_list

    def get_usb_ext_list(self):
        # Obtém uma lista de padrões de regex para corresponder a dispositivos USB estendidos
        usb_ext_list = list(USB_EXT_REGEX)
        if self.map_hubs:
            usb_ext_list.append(USB_HUBP_REGEX)
        return usb_ext_list

    def get_matching_controller(self, controller_name, from_cont=None, into_cont=None):
        # Obtém um controlador correspondente com base em vários critérios
        self.check_controllers()
        from_cont = from_cont if from_cont is not None else self.controllers
        into_cont = into_cont if into_cont is not None else self.merged_list
        if controller_name not in from_cont:
            print(f"Controlador '{controller_name}' não encontrado em 'from_cont'.")
            return None
        for check in ("locationid", "pci_debug", "ioservice_path", "acpi_path"):
            cont_adj = next((x for x in into_cont if from_cont[controller_name].get(check, None) == into_cont[x].get(check, "Unknown")), None)
            if cont_adj:
                return cont_adj
        print(f"Nenhum controlador correspondente encontrado para '{controller_name}' usando critérios de fallback.")
        return None
    
    def merge_controllers(self, from_cont=None, into_cont=None):
        # Mescla controladores de um dicionário para outro
        self.check_controllers()
        from_cont = from_cont if from_cont is not None else self.controllers
        into_cont = into_cont if into_cont is not None else self.merged_list
        for cont in from_cont:
            cont_adj = self.get_matching_controller(cont, from_cont, into_cont)
            if not cont_adj:
                print(f"Nenhum controlador correspondente encontrado para '{cont}'. Usando o nome original.")
                cont_adj = cont
            last_step = into_cont
            for step in (cont_adj, "ports"):
                if step not in last_step:
                    last_step[step] = {}
                last_step = last_step[step]
            for key in from_cont[cont]:
                if key == "ports":
                    continue
                into_cont[cont_adj][key] = from_cont[cont][key]
            for port_num in from_cont[cont]["ports"]:
                port = from_cont[cont]["ports"][port_num]
                mort = into_cont[cont_adj]["ports"].get(port_num, {})
                for key in port:
                    if key == "items":
                        new_items = []
                        for x in mort.get("items", []) + port.get("items", []):
                            if x not in new_items:
                                new_items.append(x)
                        mort["items"] = new_items
                    elif key == "enabled":
                        if port.get(key, None) is not None and mort.get(key, None) is None:
                            mort[key] = port[key]
                    elif key in ("name", "id") and key in mort:
                        continue
                    else:
                        mort[key] = port[key]
                into_cont[cont_adj]["ports"][port_num] = mort
        return into_cont
                # ... código anterior ...

    def merge_controllers(self, from_cont=None, into_cont=None):
        # Mescla controladores de um dicionário para outro
        self.check_controllers()
        from_cont = from_cont if from_cont is not None else self.controllers
        into_cont = into_cont if into_cont is not None else self.merged_list
        for cont in from_cont:
            cont_adj = self.get_matching_controller(cont, from_cont, into_cont)
            if not cont_adj:
                print(f"Nenhum controlador correspondente encontrado para '{cont}'. Usando o nome original.")
                cont_adj = cont
            last_step = into_cont
            for step in (cont_adj, "ports"):
                if step not in last_step:
                    last_step[step] = {}
                last_step = last_step[step]
            for key in from_cont[cont]:
                if key == "ports":
                    continue
                into_cont[cont_adj][key] = from_cont[cont][key]
            for port_num in from_cont[cont]["ports"]:
                port = from_cont[cont]["ports"][port_num]
                mort = into_cont[cont_adj]["ports"].get(port_num, {})
                for key in port:
                    if key == "items":
                        new_items = []
                        for x in mort.get("items", []) + port.get("items", []):
                            if x not in new_items:
                                new_items.append(x)
                        mort["items"] = new_items
                    elif key == "enabled":
                        if port.get(key, None) is not None and mort.get(key, None) is None:
                            mort[key] = port[key]
                    elif key in ("name", "id") and key in mort:
                        continue
                    else:
                        mort[key] = port[key]
                into_cont[cont_adj]["ports"][port_num] = mort
        return into_cont

    def save_plist(self, controllers=None):
        # Salva o dicionário de controladores no arquivo USB.plist
        if controllers is None:
            controllers = self.merged_list
        self.sanitize_controllers(controllers)
        try:
            with open(self.usb_list, "wb") as f:
                plistlib.dump(controllers, f, sort_keys=False)
            return True
        except Exception as e:
            print(f"Não foi possível salvar em USB.plist: {e}")
            return False

    def sanitize_controllers(self, controllers=None):
        # ... restante do código ...
        # Salva o dicionário de controladores no arquivo USB.plist
        if controllers is None:
            controllers = self.merged_list
        self.sanitize_controllers(controllers)
        try:
            with open(self.usb_list, "wb") as f:
                plistlib.dump(controllers, f, sort_keys=False)
            return True
        except Exception as e:
            print(f"Não foi possível salvar em USB.plist: {e}")
            return False

    def sanitize_controllers(self, controllers=None):
        # Remove sequências de escape ANSI dos nomes de porta no dicionário de controladores
        if controllers is None:
            controllers = self.merged_list
        for controller in controllers:
            if "ports" not in controllers[controller]:
                continue
            for port in controllers[controller]["ports"]:
                controllers[controller]["ports"][port]["items"] = [
                    x.replace(self.rs, "").replace(self.ce, "") for x in controllers[controller]["ports"][port]["items"]
                ]

    def sanitize_ioreg(self, ioreg):
        # Limpa a saída do ioreg, removendo quebras de linha em nomes de dispositivos
        return_list = isinstance(ioreg, list)
        if return_list:
            ioreg = "\n".join(ioreg)
        new_ioreg = ""
        for line in ioreg.split("\n"):
            new_ioreg += line + (" " if "+-o" in line and not " <class" in line else "\n")
        return new_ioreg.split("\n") if return_list else new_ioreg

    def populate_ioreg(self):
        # Popula o dicionário ioreg a partir de um arquivo local ou do comando ioreg
        try:
            if os.path.exists(IOREG_DUMP_PATH):
                with open(IOREG_DUMP_PATH, "rb") as f:
                    ioreg = f.read().decode("utf-8", errors="ignore").split("\n")
                    self.i.ioreg = {"IOService": ioreg}
                self.local_ioreg = True
            else:
                ioreg = self.i.get_ioreg()
            return self.sanitize_ioreg(ioreg)
        except Exception as e:
            print(f"Erro ao popular ioreg: {e}")
            return []

    def check_controllers(self):
        # Verifica e atualiza a lista de controladores
        if not self.controllers:
            self.controllers = self.populate_controllers()
        if not self.controllers:
            print("Nenhum controlador encontrado!")
            return {}
        controller_copy = {}
        for key in self.controllers:
            controller_copy[key] = self.controllers[key]
        return controller_copy

    def check_by_ioreg(self, force=False):
        # Verifica e atualiza o dicionário by_ioreg
        if force or not self.by_ioreg:
            self.by_ioreg = self.get_by_ioreg()
        if not self.by_ioreg:
            print("Nenhuma informação de porta encontrada no ioreg!")
            return {}
        return self.by_ioreg

    def get_obj_from_line(self, line):
        # Extrai informações de uma linha do ioreg
        try:
            return {
                "line": line,
                "indent": len(line) - len(line.lstrip()),
                "id": line.split("id ")[-1],
                "name": line.lstrip().split(" <class")[0],
                "type": line.split("<class ")[1].split(",")[0],
                "items": {},
            }
        except Exception as e:
            print(f"Erro ao analisar a linha do ioreg: {e}")
            return None

    def get_by_ioreg(self):
        # Obtém um dicionário de portas e seus dispositivos AppleUSB correspondentes
        try:
            if os.path.exists(IOREG_DUMP_PATH):
                with open(IOREG_DUMP_PATH, "rb") as f:
                    ioreg = f.read().decode("utf-8", errors="ignore")
                self.local_ioreg = True
            else:
                ioreg = self.r.run({"args": ["ioreg", "-c", "IOUSBDevice", "-w0"]})[0]
            ioreg = self.sanitize_ioreg(ioreg)
            port_map = self.get_port_map_list()
            valid = [
                x.replace("|", " ").replace("+-o ", "").split(", registered")[0]
                for x in ioreg.split("\n")
                if any((y.search(x) for y in self.get_map_list()))
            ]
            ports = {"items": {}}
            addrs = []
            path = []
            for line in valid:
                if not (USB_CONT_REGEX.search(line) or (self.map_hubs and USB_HUB_REGEX.search(line))):
                    try:
                        addr = line.split("@")[-1].split("<class ")[0].strip()
                        if addr not in addrs:
                            addrs.append(addr)
                    except Exception as e:
                        print(f"Erro ao obter o endereço: {e}")
                obj = self.get_obj_from_line(line)
                if not obj:
                    continue
                if path:
                    for p in path[::-1]:
                        if p["indent"] >= obj["indent"]:
                            del path[-1]
                        else:
                            break
                if USB_CONT_REGEX.search(line):
                    path = [obj]
                    continue
                if not path:
                    continue
                path.append(obj)
                if any((x.search(line) for x in USB_EXT_REGEX)):
                    map_hub = True
                    if any(("XHCI" in x["type"] for x in path)):
                        if USB_HUBP_REGEX.search(path[-1]["line"]):
                            continue
                        path = [x for x in path if not USB_HUBP_REGEX.search(x["line"])]
                        map_hub = False
                    last_root = ports
                    for p in path:
                        if p["type"] == "IOUSBHostDevice":
                            map_hub = False
                        p["map_hub"] = map_hub
                        if p["id"] not in last_root["items"]:
                            last_root["items"][p["id"]] = p
                        last_root = last_root["items"][p["id"]]
            self.all_addrs = addrs
            return ports
        except Exception as e:
            print(f"Erro ao obter informações de porta do ioreg: {e}")
            return {}

    def get_sp_usb(self, indent="    "):
        # Coleta informações USB do system_profiler
        sp_usb_list = []
        try:
            if self.local_ioreg:
                if os.path.exists(SYSTEM_PROFILER_DUMP_PATH):
                    with open(SYSTEM_PROFILER_DUMP_PATH, "rb") as f:
                        sp_usb_xml = plistlib.load(f)
                else:
                    print(f"Arquivo '{SYSTEM_PROFILER_DUMP_PATH}' não encontrado. Ignorando os dados do system_profiler.")
                    return sp_usb_list
            else:
                sp_usb_xml = plistlib.loads(
                    self.r.run({"args": ["system_profiler", "-xml", "-detaillevel", "mini", "SPUSBDataType"]})[0]
                )
            items_list = []
            for top in sp_usb_xml:
                if "_items" in top:
                    items_list.extend(top["_items"])
            while items_list:
                item = items_list.pop()
                if "location_id" in item:
                    try:
                        item["location_id_adjusted"] = item["location_id"][2:].split()[0]
                    except Exception as e:
                        print(f"Erro ao ajustar location_id: {e}")
                        continue
                    if "indent" not in item:
                        item["indent"] = ""
                    sp_usb_list.append(item)
                if "_items" in item:
                    new_items = item.pop("_items")
                    for i in new_items:
                        i["indent"] = item.get("indent", "") + indent
                    items_list.extend(new_items)
            return sp_usb_list
        except Exception as e:
            print(f"Erro ao obter informações USB do system_profiler: {e}")
            return []
    
    def map_inheritance(self, top_level, level=1, indent="    "):
        # Mapeia a hierarquia de dispositivos USB
        if "items" not in top_level:
            return []
        text = []
        for v in top_level["items"]:
            check_entry = top_level["items"][v]
            is_hub = USB_HUB_REGEX.search(check_entry.get("line", "Unknown"))
            try:
                name, addr = check_entry.get("name", "Unknown").split("@")
            except:
                addr = "Unknown"
                name = check_entry.get("name", check_entry.get("type", "Unknown"))
            value = (indent * level) + "- {}{}".format(
                name, " (HUB-{})".format(addr) if is_hub and check_entry.get("map_hub", False) and self.map_hubs else ""
            )
            text.append((value, name))
            if is_hub and check_entry.get("map_hub", False) and self.map_hubs:
                continue
            if len(check_entry.get("items", [])):
                text.extend(self.map_inheritance(check_entry, level + 1))
        return text

    def get_port_from_dict(self, port_id, top_level):
        # Obtém uma porta específica de um dicionário
        if port_id in top_level["items"]:
            return top_level["items"][port_id]
        for port in top_level["items"]:
            test_port = self.get_port_from_dict(port_id, top_level["items"][port])
            if test_port:
                return test_port
        return None
    
    def get_items_for_port(self, port_id, indent="    "):
        # Obtém itens para uma porta específica
        port = self.get_port_from_dict(port_id, self.check_by_ioreg())
        if not port:
            return []
        return self.map_inheritance(port)

    def get_ports_and_devices_for_controller(self, controller, sp_usb_list=[], indent="    "):
        # Obtém portas e dispositivos para um controlador específico
        self.check_controllers()
        if controller not in self.controllers:
            print(f"Controlador {controller} não encontrado!")
            return OrderedDict()
        port_dict = OrderedDict()
        port_addrs = [self.controllers[controller]["ports"][p]["address"] for p in self.controllers[controller]["ports"]]
        dupe_addrs = [x for x in port_addrs if port_addrs.count(x) > 1]
        for port_num in sorted(self.controllers[controller]["ports"]):
            port = self.controllers[controller]["ports"][port_num]
            port_num_dec = self.hex_dec(self.hex_swap(port["port"]))
            entry_name = "{} | {} | {} | {} | {} | {} | {}".format(
                port["name"],
                port["type"],
                port["port"],
                port["address"],
                port.get("connector", -1),
                controller,
                self.controllers[controller]["parent"],
            )
            inheritance = self.get_items_for_port(port["id"], indent=indent)
            port_dict[entry_name] = [x[0] for x in inheritance]
            names = [x[1] for x in inheritance]
            for item in sp_usb_list:
                try:
                    l_id = item["location_id_adjusted"]
                    name = item["_name"].lstrip()
                except:
                    continue
                if l_id in self.all_addrs:
                    closest_addr = l_id
                else:
                    l_id_strip = l_id.rstrip("0")
                    closest_addr = None
                    for addr in self.all_addrs:
                        addr_strip = addr.rstrip("0")
                        if l_id_strip == addr_strip:
                            closest_addr = addr
                            break
                        if l_id_strip.startswith(addr_strip) and (
                            not closest_addr or len(addr_strip) > len(closest_addr.rstrip("0"))
                        ):
                            closest_addr = addr
                if closest_addr != port["address"]:
                    continue
                if name in names:
                    continue
                ind = item.get("indent", indent)[
                      len(indent) * self.controllers[controller].get("nest_level", 0):
                      ]
                port_dict[entry_name].append(
                    "{}* {}{}{}".format(
                        ind,
                        self.rs if port["address"] in dupe_addrs else "",
                        name,
                        self.ce if port["address"] in dupe_addrs else "",
                    )
                )
        return port_dict

    def get_ports_and_devices(self, indent="    "):
        # Obtém um dicionário de todas as portas e seus dispositivos conectados
        self.check_controllers()
        port_dict = OrderedDict()
        sp_usb_list = self.get_sp_usb()
        for x in self.controllers:
            port_dict.update(self.get_ports_and_devices_for_controller(x, sp_usb_list=sp_usb_list, indent=indent))
        return port_dict

    def get_populated_count_for_controller(self, controller):
        # Obtém a contagem de portas populadas para um controlador
        port_dict = self.get_ports_and_devices_for_controller(controller)
        return len([x for x in port_dict if len(port_dict[x])])

    def get_ioservice_path(self, check_line):
        # Obtém o caminho do IOService para um dispositivo
        line_id = "id " + check_line.split(", registered")[0].split("id ")[-1]
        for index, line in enumerate(self.ioreg):
            if line_id in line:
                indent = -1
                path = []
                for l in self.ioreg[index::-1]:
                    if " <class" not in l:
                        continue
                    l_check = l.replace("|", " ").replace("+-o", "")
                    i_check = len(l_check) - len(l_check.lstrip())
                    if i_check < indent or indent == -1:
                        entry = l_check.lstrip().split(" <class")[0]
                        if entry == self.smbios:
                            break
                        path.append(entry)
                        indent = i_check
                return "IOService:/" + "/".join(path[::-1])
        return None
    
    def populate_controllers(self):
        # Popula o dicionário de controladores a partir do ioreg
        if self.ioreg is None:
            print("Nenhum ioreg encontrado para iterar!")
            return {}
        self.smbios = None
        port_map = self.get_port_map_list()
        controllers = OrderedDict()
        map_list = self.get_map_list()
        map_list.extend(
            [
                re.compile(r"<class IOPlatformExpertDevice,"),
                re.compile(r"<class IOPCIDevice,"),
            ]
        )
        valid = [
            (x.replace("|", " ").replace("+-o ", "").split(", registered")[0], i)
            for i, x in enumerate(self.ioreg)
            if any((y.search(x) for y in map_list))
        ]
        cont_list = []
        last_port = None
        last_pci = None
        for line, i in valid:
            if "<class IOPlatformExpertDevice," in line:
                self.smbios = line.split("<class")[0].strip()
                continue
            elif "<class IOPCIDevice," in line:
                last_pci = (line, i)
                continue
            obj = self.get_obj_from_line(line)
            if not obj:
                continue
            obj["full_name"] = obj["name"]
            obj["name"] = obj["full_name"].split("@")[0]
            obj["address"] = obj["full_name"].split("@")[-1]
            obj["items"] = []
            if cont_list:
                for c in cont_list[::-1]:
                    if controllers[c]["indent"] >= obj["indent"]:
                        del cont_list[-1]
                    else:
                        break
            if USB_CONT_REGEX.search(line):
                last_controller = obj["full_name"]
                obj["ports"] = OrderedDict()
                obj["index"] = i
                controllers[last_controller] = obj
                cont_list = [last_controller]
                last_port = None
                if not last_pci or last_pci[1] + 1 >= len(self.ioreg):
                    print("Aviso: Informações PCI ausentes ou incompletas para o controlador atual.")
                    continue
                obj["parent"] = last_pci[0].strip().split(" <class")[0]
                obj["parent_name"], temp_addr = obj["parent"].split("@")
                obj["parent_index"] = last_pci[1]
                try:
                    major, minor = temp_addr.split(",") if "," in temp_addr else (temp_addr, "0")
                    acpi_addr = "0x{}{}".format(major.rjust(4, "0"), minor.rjust(4, "0"))
                    obj["acpi_address"] = "Zero" if acpi_addr == "0x00000000" else acpi_addr
                except Exception as e:
                    print(f"Erro ao analisar o endereço ACPI: {e}")
                for line in self.ioreg[last_pci[1] + 1:]:
                    if line.replace("|", "").strip() == "}":
                        break
                    elif '"acpi-path"' in line:
                        try:
                            obj["acpi_path"] = line.split('"')[-2]
                        except Exception as e:
                            print(f"Erro ao obter o caminho ACPI: {e}")
                    elif '"pcidebug"' in line:
                        try:
                            obj["pci_debug"] = line.split('"')[-2]
                        except Exception as e:
                            print(f"Erro ao obter informações de depuração PCI: {e}")
                    if obj.get("acpi_path") and obj.get("pci_debug"):
                        break
            elif not cont_list:
                continue
            elif self.map_hubs and USB_HUB_REGEX.search(line) and "EHCI" in controllers[cont_list[0]]["type"]:
                last_controller = "HUB-{}".format(obj["address"])
                obj["ports"] = OrderedDict()
                obj["index"] = i
                obj["is_hub"] = True
                obj["locationid"] = self.hex_dec(obj["address"])
                obj["parent"] = last_controller
                obj["parent_name"] = controllers[cont_list[0]]["name"]
                obj["nest_level"] = len(cont_list)
                controllers[last_controller] = obj
                if last_port:
                    last_port["contains_hub"] = True
                cont_list.append(last_controller)
            elif any((x.search(line) for x in port_map)):
                if USB_HUBP_REGEX.search(line) and "EHCI" not in controllers[cont_list[0]]["type"]:
                    continue
                if i + 1 >= len(self.ioreg):
                    print("Aviso: Informações da porta ausentes ou incompletas para a porta atual.")
                    continue
                for line in self.ioreg[i + 1:]:
                    if line.replace("|", "").strip() == "}":
                        break
                    elif '"port" = ' in line:
                        obj["port"] = line.split("<")[1].split(">")[0]
                    elif '"UsbConnector" = ' in line:
                        try:
                            obj["connector"] = int(line.split(" = ")[1].strip())
                        except:
                            obj["connector"] = -1
                    elif '"comment" = "' in line.lower():
                        try:
                            obj["ioreg_comment"] = line.split('"')[-2]
                        except:
                            pass
                    if all((obj.get(x) for x in ("port", "connector", "ioreg_comment"))):
                        break
                controllers[cont_list[-1]]["ports"][obj["port"]] = obj
                last_port = obj
        for controller in controllers:
            if controllers[controller].get("is_hub"):
                continue
            path = self.get_ioservice_path(controllers[controller]["line"])
            if not path:
                continue
            controllers[controller]["ioservice_path"] = path
        return controllers

    def build_kext(self, modern=True, legacy=False, dummy=False, padded_to=0, skip_disabled=False, force_matching=None):
        if not modern and not legacy:
            return
        self.u.resize(80, 24)
        empty_controllers = []
        skip_empty = True
        if padded_to <= 0:
            for x in self.merged_list:
                ports = self.merged_list[x]["ports"]
                if all((ports[y].get("enabled", False) == False for y in ports)):
                    empty_controllers.append(x)
            if len(empty_controllers):
                if all((x in empty_controllers for x in self.merged_list)):
                    self.u.head("Nenhuma porta selecionada")
                    print("")
                    print("Não há portas habilitadas!")
                    print("Por favor, habilite pelo menos uma porta e tente novamente.")
                    print("")
                    self.u.grab("Pressione [enter] para retornar ao menu...")
                    return
                while True:
                    self.u.head("Validação do controlador")
                    print("")
                    print("Controladores vazios encontrados!")
                    print(
                        "Os seguintes controladores não possuem portas habilitadas:\n"
                    )
                    for x in empty_controllers:
                        print(f" - {x}")
                    print("")
                    e = self.u.grab(
                        "Escolha (i)gnorar ou (d)esabilitá-los: "
                    ).lower()
                    if e in ("i", "ignore", "d", "disable"):
                        skip_empty = e in ("i", "ignore")
                        break
        title = []
        if modern:
            title.append(
                os.path.basename(self.dummy_kext_path if dummy else self.kext_path)
            )
        if legacy:
            title.append(
                os.path.basename(
                    self.dummy_legacy_kext_path if dummy else self.legacy_kext_path
                )
            )
        self.u.head(f"Construir {' e '.join(title)}")
        print("")
        os.chdir(self.script_dir)
        print(
            "Gerando Info.plist{}...".format(
                "" if len(title) == 1 else "s"
            )
        )
        reveal = None
        if modern:
            reveal = self.dummy_kext_path if dummy else self.kext_path
            self.check_and_build(
                reveal,
                self.dummy_info_path if dummy else self.info_path,
                skip_empty=skip_empty,
                legacy=False,
                skip_disabled=skip_disabled,
                padded_to=padded_to,
                force_matching=force_matching,
            )
        if legacy:
            if not reveal:
                reveal = (
                    self.dummy_legacy_kext_path
                    if dummy
                    else self.legacy_kext_path
                )
            self.check_and_build(
                self.dummy_legacy_kext_path
                if dummy
                else self.legacy_kext_path,
                self.dummy_legacy_info_path
                if dummy
                else self.legacy_info_path,
                skip_empty=skip_empty,
                legacy=True,
                skip_disabled=skip_disabled,
                padded_to=padded_to,
                force_matching=force_matching,
            )
        print("Concluído.")
        print("")
        if reveal:
            self.re.reveal(reveal, True)
        self.u.grab("Pressione [enter] para retornar ao menu...")

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

    def build_info_plist(
        self,
        skip_empty=True,
        legacy=False,
        skip_disabled=False,
        padded_to=0,
        force_matching=None,
    ):
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

    def check_hex(self, value):
        return re.sub(r"[^0-9A-Fa-f]+", "", value.lower().replace("0x", ""))

    def hex_to_data(self, value):
        return binascii.unhexlify(self.check_hex(value).encode("utf-8"))
        return plistlib.UUID(binascii.unhexlify(self.check_hex(value).encode("utf-8")))
    def hex_swap(self, value):
        input_hex = self.check_hex(value)
        if not len(input_hex):
            return None
        input_hex = list("0" * (len(input_hex) % 2) + input_hex)
        hex_pairs = [input_hex[i : i + 2] for i in range(0, len(input_hex), 2)]
        hex_rev = hex_pairs[::-1]
        hex_str = "".join(["".join(x) for x in hex_rev])
        return hex_str.upper()

    def hex_dec(self, value):
        value = self.check_hex(value)
        try:
            dec = int(value, 16)
        except:
            return None
        return dec

    def port_to_num(self, value, pad_to=2):
        value = self
       # ... código anterior ...

    def hex_swap(self, value):
        input_hex = self.check_hex(value)
        if not len(input_hex):
            return None
        input_hex = list("0" * (len(input_hex) % 2) + input_hex)
        hex_pairs = [input_hex[i : i + 2] for i in range(0, len(input_hex), 2)]
        hex_rev = hex_pairs[::-1]
        hex_str = "".join(["".join(x) for x in hex_rev])
        return hex_str.upper()

    def hex_dec(self, value):
        value = self.check_hex(value)
        try:
            dec = int(value, 16)
        except:
            return None
        return dec

    def port_to_num(self, value, pad_to=2):
        value = self.check_hex(value)
        try:
            return str(int(self.hex_swap(value), 16)).rjust(pad_to)
        except:
            pass
        return "-1".rjust(pad_to)

    # ... restante do código ...
        try:
            return str(int(self.hex_swap(value), 16)).rjust(pad_to)
        except:
            pass
        return "-1".rjust(pad_to)

    def discover_ports(self):
        self.check_controllers()
        self.merged_list = self.merge_controllers()
        total_ports = OrderedDict()
        last_ports = OrderedDict()
        last_list = []
        while True:
            extras = index = 0
            last_w = 80
            self.check_by_ioreg(force=True)
            self.u.head("Descobrir portas USB")
            print("")
            check_ports = self.get_ports_and_devices()
            new_last_list = []
            for i, x in enumerate(check_ports):
                if len(check_ports[x]) > len(total_ports.get(x, [])):
                    total_ports[x] = [y for y in check_ports[x]]
                if last_ports and len(check_ports[x]) > len(last_ports.get(x, [])):
                    new_last_list.append((i + 1, x))
            if new_last_list:
                last_list = [x for x in new_last_list]
            for x in check_ports:
                last_ports[x] = [y for y in check_ports[x]]
            last_cont = None
            cont_count = {}
            show_red_warning = False
            pad = 11
            for index, port in enumerate(check_ports):
                n, t, p, a, e, c, r = port.split(" | ")
                if len(total_ports.get(port, [])):
                    cont_count[c] = cont_count.get(c, 0) + 1
                if last_cont != c:
                    print(
                        f"    ----- {self.cs}{r} Controller{self.ce} -----"
                    )
                    last_cont = c
                    extras += 1
                line = "{}. {} | {} | {} ({}) | {} | Type {}".format(
                    str(index + 1).rjust(2),
                    n,
                    t,
                    self.port_to_num(p),
                    p,
                    a,
                    e,
                )
                if len(line) > last_w:
                    last_w = len(line)
                print(
                    "{}{}{}".format(
                        self.cs
                        if any((port == x[1] for x in last_list))
                        else self.bs
                        if len(total_ports.get(port, []))
                        else "",
                        line,
                        self.ce if len(total_ports.get(port, [])) else "",
                    )
                )
                if last_cont == None:
                    last_cont = c
                original = self.controllers[c]["ports"][p]
                merged_c = self.get_matching_controller(
                    c, self.controllers, self.merged_list
                )
                if not merged_c:
                    merged_c = c
                last_step = self.merged_list
                for step in (merged_c, "ports", p):
                    if step not in last_step:
                        last_step[step] = {}
                    last_step = last_step[step]
                merged_p = self.merged_list[merged_c]["ports"][p]
                if len(total_ports.get(port, [])):
                    new_items = original.get("items", [])
                    new_items.extend(
                        [
                            x
                            for x in total_ports[port]
                            if x not in original.get("items", [])
                        ]
                    )
                    original["items"] = new_items
                    original["enabled"] = True
                if merged_p.get("comment"):
                    extras += 1
                    print(
                        "    {}{}{}".format(
                            self.nm, merged_p["comment"], self.ce
                        )
                    )
                if (
                    merged_p.get("ioreg_comment")
                    and merged_p["ioreg_comment"] != merged_p.get("comment")
                ):
                    extras += 1
                    print(
                        "    {}{}{} (from ioreg)".format(
                            self.nm, merged_p["ioreg_comment"], self.ce
                        )
                    )
                if len(check_ports[port]):
                    extras += len(check_ports[port])
                    print("\n".join(check_ports[port]))
                    if any(
                        (
                            self.rs in red_check
                            for red_check in check_ports[port]
                        )
                    ):
                        show_red_warning = True
            print("")
            if show_red_warning:
                pad = 13
                print(
                    "- Itens em {}VERMELHO{} não possuem endereçamento preciso\n".format(
                        self.rs, self.ce
                    )
                )
            print("Populada:")
            pop_list = []
            for cont in self.controllers:
                try:
                    parent = self.controllers[cont]["parent"]
                except:
                    parent = cont
                count = cont_count.get(cont, 0)
                pop_list.append(
                    "{}{}: {:,}{}".format(
                        self.cs if 0 < count < 16 else self.rs,
                        parent.split("@")[0],
                        count,
                        self.ce,
                    )
                )
            print(", ".join(pop_list))
            temp_h = index + 1 + extras + pad + (1 if last_list else 0)
            h = temp_h if temp_h > 24 else 24
            self.u.resize(last_w, h)
            print("Pressione Q e [enter] para parar")
            if last_list:
                print(
                    "Pressione N e [enter] para apelidar a(s) porta(s) {}".format(
                        ", ".join([str(x[0]) for x in last_list])
                    )
                )
            print("")
            out = self.u.grab(
                "Aguardando {:,} segundo{}:  ".format(
                    self.discover_wait,
                    "" if self.discover_wait == 1 else "s",
                ),
                timeout=self.discover_wait,
            )
            if out is None or not len(out):
                continue
            if out.lower() == "q":
                break
            if out.lower() == "n" and last_list:
                self.get_name(last_list)
        self.merged_list = self.merge_controllers()
        self.save_plist()

    def get_name(self, port_list):
        originals = []
        name_list = []
        pad = 11
        for index, port in port_list:
            n, t, p, a, e, c, r = port.split(" | ")
            if c not in self.merged_list:
                print(f"Controlador '{c}' não encontrado em merged_list.")
                continue
            if p not in self.merged_list[c]["ports"]:
                print(f"Porta '{p}' não encontrada em merged_list para o controlador '{c}'.")
                continue
            original = self.merged_list[c]["ports"][p]
            originals.append(original)
            nickname = original.get("comment", None)
            name_list.append(
                "{}{}. {}{} = {}:\n{}".format(
                    self.cs,
                    index,
                    n,
                    self.ce,
                    self.nm + nickname + self.ce if nickname else "None",
                    "\n".join(original.get("items", [])),
                )
            )
        name_text = "\n".join(name_list)
        temp_h = len(name_text.split("\n")) + pad
        h = temp_h if temp_h > 24 else 24
        self.u.resize(80, h)
        while True:
            self.u.head("Apelido da porta")
            print("")
            print("Números de porta, nomes, apelidos e dispositivos atuais:\n")
            print(name_text)
            print("")
            print("C. Limpar nomes personalizados")
            print("Q. Retornar à descoberta")
            print("")
            menu = self.u.grab(
                "Digite um apelido para a(s) porta(s) {} {}:  ".format(
                    "" if len(port_list) == 1 else "s",
                    ", ".join([str(x[0]) for x in port_list]),
                )
            )
            if not len(menu):
                continue
            if menu.lower() in ("c", "none"):
                for original in originals:
                    original.pop("comment", None)
                return
            elif menu.lower() == "q":
                return
            for original in originals:
                original["comment"] = menu
            return

    def print_types(self):
        self.u.resize(80, 24)
        self.u.head("Tipos USB")
        print("")
        types = "\n".join(
            [
                f"{key}: {value}"
                for key, value in USB_TYPES.items()
            ]
        )
        print(types)
        print("")
        print("De acordo com a especificação ACPI 6.2.")
        print("")
        self.u.grab("Pressione [enter] para retornar ao menu...")
        return

    def edit_plist(self):
        os.chdir(self.script_dir)
        pad = 29
        path_match = False
        while True:
            self.u.resize(80, 24)
            self.save_plist()
            ports = []
            extras = 0
            last_w = 80
            self.u.head("Editar portas USB")
            print("")
            if not self.merged_list:
                print(
                    "Nenhuma porta foi descoberta ainda! Use o modo de descoberta no menu principal primeiro."
                )
                print("")
                return self.u.grab(
                    "Pressione [enter] para retornar ao menu..."
                )
            custom_name = ioreg_name = False
            index = 0
            counts = OrderedDict()
            for cont in self.merged_list:
                print(
                    "    ----- {}{} Controller{} -----".format(
                        self.cs, self.merged_list[cont]["parent"], self.ce
                    )
                )
                extras += 1
                counts[cont] = 0
                for port_num in sorted(self.merged_list[cont]["ports"]):
                    index += 1
                    port = self.merged_list[cont]["ports"][port_num]
                    ports.append(port)
                    if port.get("enabled", False):
                        counts[cont] += 1
                    usb_connector = port.get(
                        "type_override",
                        255
                        if port.get("contains_hub")
                        else port.get("connector", -1),
                    )
                    if usb_connector == -1:
                        usb_connector = (
                            3 if "XHCI" in self.merged_list[cont]["type"] else 0
                        )
                    line = "[{}] {}. {} | {} | {} ({}) | {} | Type {}".format(
                        "#" if port.get("enabled", False) else " ",
                        str(index).rjust(2),
                        port["name"],
                        port["type"],
                        self.port_to_num(port["port"]),
                        port["port"],
                        port["address"],
                        usb_connector,
                    )
                    if len(line) > last_w:
                        last_w = len(line)
                    print(
                        "{}{}{}".format(
                            self.bs if port.get("enabled", False) else "",
                            line,
                            self.ce if port.get("enabled", False) else "",
                        )
                    )
                    if port.get("comment", None):
                        extras += 1
                        print(
                            "    {}{}{}".format(
                                self.nm, port["comment"], self.ce
                            )
                        )
                    if (
                        port.get("ioreg_comment")
                        and port["ioreg_comment"] != port.get("comment")
                    ):
                        ioreg_name = True
                        extras += 1
                        print(
                            "    {}{}{} (from ioreg)".format(
                                self.nm, port["ioreg_comment"], self.ce
                            )
                        )
                    if len(port.get("items", [])):
                        extras += len(port["items"])
                        print("\n".join(port["items"]))
            print("")
            print("Populada:")
            pop_list = []
            for cont in counts:
                try:
                    parent = self.merged_list[cont]["parent"]
                except:
                    parent = cont
                pop_list.append(
                    "{}{}: {:,}{}".format(
                        self.cs if 0 < counts[cont] < 16 else self.rs,
                        parent.split("@")[0],
                        counts[cont],
                        self.ce,
                    )
                )
            print(", ".join(pop_list))
            print("")
            print("K. Construir USBMap.kext (Catalina e mais recentes)")
            print(
                "   - AppleUSBHostMergeProperties, MinKernel=19.0.0"
            )
            print("L. Construir USBMapLegacy.kext (Mojave e mais antigos)")
            print("   - AppleUSBMergeNub, MaxKernel=18.9.9")
            print("B. Construir USBMap.kext e USBMapLegacy.kext")
            print("A. Selecionar todos")
            print("N. Selecionar nenhum")
            print("P. Habilitar todas as portas povoadas")
            print("D. Desabilitar todas as portas vazias")
            print("C. Limpar itens detectados")
            print("T. Mostrar tipos")
            if path_match:
                print("H. Usar IOParentMatch (atualmente IOPathMatch)")
            else:
                print("H. Usar IOPathMatch (atualmente IOParentMatch)")
            if ioreg_name:
                extras += 1
                print("I. Usar todos os nomes personalizados do IOReg")
            print("")
            print("M. Menu principal")
            print("Q. Sair")
            print("")
            print(
                "- Selecione as portas para alternar com listas delimitadas por vírgulas (por exemplo, 1,2,3,4,5)"
            )
            print(
                "- Defina um intervalo de portas usando esta fórmula R:1-15:On/Off"
            )
            print(
                "- Altere os tipos usando esta fórmula T:1,2,3,4,5:t onde t é o tipo"
            )
            print(
                "- Defina nomes personalizados usando esta fórmula C:1,2:Nome - Nome = Nenhum para limpar"
            )
            temp_h = index + 1 + extras + pad
            h = temp_h if temp_h > 24 else 24
            self.u.resize(last_w, h)
            menu = self.u.grab("Faça a sua seleção:  ")
            if not len(menu):
                continue
            elif menu.lower() == "q":
                self.u.resize(80, 24)
                self.u.custom_quit()
            elif menu.lower() == "m":
                return
            elif menu.lower() == "k":
                self.build_kext(
                    modern=True,
                    legacy=False,
                    force_matching="IOPathMatch" if path_match else None,
                )
            elif menu.lower() == "l":
                self.build_kext(
                    modern=False,
                    legacy=True,
                    force_matching="IOPathMatch" if path_match else None,
                )
            elif menu.lower() == "b":
                self.build_kext(
                    modern=True,
                    legacy=True,
                    force_matching="IOPathMatch" if path_match else None,
                )
            elif menu.lower() in ("n", "a"):
                for port in ports:
                    port["enabled"] = True if menu.lower() == "a" else False
            elif menu.lower() == "p":
                for port in ports:
                    if port.get("items", []):
                        port["enabled"] = True
            elif menu.lower() == "d":
                for port in ports:
                    if not port.get("items", []):
                        port["enabled"] = False
            elif menu.lower() == "c":
                for port in ports:
                    port["items"] = []
            elif menu.lower() == "t":
                self.print_types()
            elif menu.lower() == "h":
                path_match ^= True
            elif menu.lower() == "i" and ioreg_name:
                for cont in self.merged_list:
                    for port_num in sorted(self.merged_list[cont]["ports"]):
                        port = self.merged_list[cont]["ports"][port_num]
                        if port.get("ioreg_comment"):
                            port["comment"] = port["ioreg_comment"]
            elif menu[0].lower() == "r":
                try:
                    nums = [
                        int(x)
                        for x in menu.split(":")[1].replace(" ", "").split("-")
                    ]
                    a, b = (
                        nums[0] - 1,
                        nums[-1] - 1,
                    )
                    if b < a:
                        a, b = b, a
                    if not all((0 <= x < len(ports) for x in (a, b))):
                        continue
                    toggle = menu.split(":")[-1].lower()
                    if toggle not in ("on", "off"):
                        continue
                    for x in range(a, b + 1):
                        ports[x]["enabled"] = toggle == "on"
                except:
                    continue
            elif menu[0].lower() == "t":
                try:
                    nums = [
                        int(x)
                        for x in menu.split(":")[1].replace(" ", "").split(",")
                    ]
                    t = int(menu.split(":")[-1])
                    for x in nums:
                        x -= 1
                        if not 0 <= x < len(ports):
                            continue
                        ports[x]["type_override"] = t
                except:
                    continue
            elif menu[0].lower() == "c":
                try:
                    nums = [
                        x.lower()
                        for x in menu.split(":")[1].replace(" ", "").split(",")
                    ]
                    if "all" in nums:
                        nums = list(range(len(ports)))
                    else:
                        nums = [int(x) for x in nums]
                    name = menu.split(":")[-1]
                    for x in nums:
                        x -= 1
                        if not 0 <= x < len(ports):
                            continue
                        if name.lower() == "none":
                            ports[x].pop("comment", None)
                        else:
                            ports[x]["comment"] = name
                except:
                    continue
            else:
                try:
                    nums = [int(x) for x in menu.replace(" ", "").split(",")]
                    for x in nums:
                        x -= 1
                        if not 0 <= x < len(ports):
                            continue
                        ports[x]["enabled"] = not ports[x].get(
                            "enabled", False
                        )
                except:
                    continue

    def get_safe_acpi_path(self, path):
        return (
            None
            if path == None
            else ".".join(
                [x.split("@")[0] for x in path.split("/") if len(x) and ":" not in x]
            )
        )

    def get_numbered_name(self, base_name, number, use_hex=True):
        if use_hex:
            number = hex(number).replace("0x", "").upper()
        else:
            number = str(number)
        return base_name[: -1 * len(number)] + number

    def generate_renames(self, cont_list):
        used_names = [x for x in self.illegal_names]
        used_names.extend(
            [
                self.connected_controllers[x]["parent_name"].upper()
                for x in self.connected_controllers
                if self.connected_controllers[x].get("parent_name", None)
            ]
        )
        self.u.head("Renomear controladores conflitantes")
        print("")
        oc_patches = {"ACPI": {"Patch": []}}
        clover_patches = {"ACPI": {"DSDT": {"Patches": []}}}
        zero = plistlib.UUID(binascii.unhexlify("00000000"))
        for cont in cont_list:
            con_type = "XHCI"
            print(f"Verificando {cont}...")
            c_type = self.connected_controllers[cont]["type"]
            if "XHCI" in c_type:
                print(" - Dispositivo XHCI")
            elif "EHCI" in c_type:
                print(" - Dispositivo EHCI")
                con_type = "EH01"
            else:
                print(" - Tipo desconhecido - usando XHCI")
            print(" - Coletando nome exclusivo...")
            starting_number = 1 if con_type == "EH01" else 2
            while True:
                name = self.get_numbered_name(con_type, starting_number)
                if name not in used_names:
                    used_names.append(name)
                    break
                starting_number += 1
            print(f" --> Obtido {name}")
            cname = cont.split("@")[0].ljust(4, "_")
            find = plistlib.UUID(cname.encode("utf-8"))
            repl = plistlib.UUID(name.encode("utf-8"))
            comm = f"Renomear {cname} para {name}"
            c_patch = {"Comment": comm, "Disabled": False, "Find": find, "Replace": repl}
            oc_patch = {
                "Base": "",
                "BaseSkip": 0,
                "Comment": comm,
                "Count": 0,
                "Enabled": True,
                "Find": find,
                "Limit": 0,
                "Mask": plistlib.UUID(b""),
                "OemTableId": zero,
                "Replace": repl,
                "ReplaceMask": plistlib.UUID(b""),
                "Skip": 0,
                "TableLength": 0,
                "TableSignature": zero,
            }
            clover_patches["ACPI"]["DSDT"]["Patches"].append(c_patch)
            oc_patches["ACPI"]["Patch"].append(oc_patch)
        print("Salvando patches_OC.plist...")
        os.chdir(self.script_dir)
        if not os.path.exists(self.output):
            os.mkdir(self.output)
        with open(self.oc_patches, "wb") as f:
            plistlib.dump(oc_patches, f)
        print("Salvando patches_Clover.plist...")
        with open(self.clover_patches, "wb") as f:
            plistlib.dump(clover_patches, f)
        self.re.reveal(self.oc_patches, True)
        print("")
        print("Concluído.")
        print("")
        self.u.grab("Pressione [enter] para retornar ao menu...")

    def generate_acpi_renames(self, cont_list):
        used_names = [x for x in self.illegal_names]
        used_names.extend(
            [
                self.connected_controllers[x]["parent_name"].upper()
                for x in self.connected_controllers
                if self.connected_controllers[x].get("parent_name", None)
            ]
        )
        self.u.head("Renomear dispositivos")
        print("")
        ssdt = """//
// SSDT para renomear PXSX, XHC1, EHC1, EHC2 e outros nomes de dispositivos conflitantes
//
DefinitionBlock ("", "SSDT", 2, "CORP", "UsbReset", 0x00001000)
{
    /*
     * Comece a copiar daqui se você estiver adicionando essas informações a um SSDT-USB-Reset!
     */

"""
        parents = []
        devices = []
        for cont in cont_list:
            con_type = "XHCI"
            print(f"Verificando {cont}...")
            c_type = self.connected_controllers[cont]["type"]
            acpi_path = self.get_safe_acpi_path(
                self.connected_controllers[cont]["acpi_path"]
            )
            if not acpi_path:
                print(" - Caminho ACPI não encontrado - ignorando.")
                continue
            acpi_parent = ".".join(acpi_path.split(".")[:-1])
            acpi_addr = self.connected_controllers[cont]["acpi_address"]
            if "XHCI" in c_type:
                print(" - Dispositivo XHCI")
            elif "EHCI" in c_type:
                print(" - Dispositivo EHCI")
                con_type = "EH01"
            else:
                print(" - Tipo desconhecido - usando XHCI")
            print(f" - Caminho ACPI: {acpi_path}")
            print(f" --> Caminho pai ACPI: {acpi_parent}")
            print(f" - ACPI _ADR: {acpi_addr}")
            print(" - Coletando nome exclusivo...")
            starting_number = 1 if con_type == "EH01" else 2
            while True:
                name = self.get_numbered_name(con_type, starting_number)
                if name not in used_names:
                    used_names.append(name)
                    break
                starting_number += 1
            print(f" --> Obtido {name}")
            parents.append(acpi_parent)
            devices.append((acpi_path, name, acpi_addr, acpi_parent))
        if not len(devices):
            print("Nenhum dispositivo válido - nada para construir.")
            print("")
            return self.u.grab("Pressione [enter] para retornar ao menu...")
        print("Construindo SSDT-USB-Reset.dsl...")
        for parent in sorted(list(set(parents))):
            ssdt += f"    External ({parent}, DeviceObj)\n"
        if len(parents):
            ssdt += "\n"
        for device in devices:
            acpi_path, name, acpi_addr, acpi_parent = device
            ssdt += f"    External ({acpi_path}, DeviceObj)\n"
            ssdt += (
                "    Scope([[device]])\n"
                "    {\n"
                "        Method (_STA, 0, NotSerialized)  // _STA: Status\n"
                "        {\n"
                '            If (_OSI ("Darwin"))\n'
                "            {\n"
                "                Return (Zero)\n"
                "            }\n"
                "            Else\n"
                "            {\n"
                "                Return (0x0F)\n"
                "            }\n"
                "        }\n"
                "    }\n\n"
                "    Scope([[parent]])\n"
                "    {\n"
                "        Device ([[new_device]])\n"
                "        {\n"
                "            Name (_ADR, [[address]])  // _ADR: Address\n"
                "            Method (_STA, 0, NotSerialized)  // _STA: Status\n"
                "            {\n"
                '                If (_OSI ("Darwin"))\n'
                "                {\n"
                "                    Return (0x0F)\n"
                "                }\n"
                "                Else\n"
                "                {\n"
                "                    Return (Zero)\n"
                "                }\n"
                "            }\n"
                "        }\n"
                "    }\n\n"
            ).replace("[[device]]", acpi_path).replace(
                "[[parent]]", acpi_parent
            ).replace(
                "[[new_device]]", name
            ).replace(
                "[[address]]", acpi_addr
            )
        ssdt += """    /*
     * Fim da cópia aqui se você estiver adicionando essas informações a um SSDT-USB-Reset!
     */
}"""
        print("Salvando em SSDT-USB-Reset.dsl...")
        os.chdir(self.script_dir)
        if not os.path.exists(self.output):
            os.mkdir(self.output)
        with open(self.ssdt_path, "w") as f:
            f.write(ssdt)
        self.re.reveal(self.ssdt_path, True)
        print("")
        print("Concluído.")
        print("")
        self.u.grab("Pressione [enter] para retornar ao menu...")

    def reset_rhubs(self, rhub_paths):
        self.u.head("Redefinir RHUBs")
        print("")
        ssdt = """//
// SSDT para redefinir dispositivos RHUB em controladores XHCI para forçar a consulta de hardware de portas
//
// AVISO: Pode conflitar com o SSDT-USB-Reset existente! Verifique os nomes e caminhos antes
// de mesclar!
//
DefinitionBlock ("", "SSDT", 2, "CORP", "RHBReset", 0x00001000)
{
    /*
     * Comece a copiar daqui se você estiver adicionando essas informações a um SSDT-USB-Reset existente!
     */

"""
       
        for rhub in sorted(list(set(rhub_paths))):
            print("Resetting {}...".format(rhub))
            ssdt += "    External ({}, DeviceObj)\n".format(rhub)
            ssdt += """
    Scope([[device]])
    {
        Method (_STA, 0, NotSerialized)  // _STA: Status
        {
            If (_OSI ("Darwin"))
            {
                Return (Zero)
            }
            Else
            {
                Return (0x0F)
            }
        }
    }

""".replace("[[device]]",rhub)
        # Add the footer
        ssdt += """    /*
     * End copying here if you're adding this info to an SSDT-USB-Reset!
     */
}"""
        print("Saving to SSDT-RHUB-Reset.dsl...")
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        if not os.path.exists(self.output): os.mkdir(self.output)
        with open(self.rsdt_path,"w") as f:
            f.write(ssdt)
        self.re.reveal(self.rsdt_path,True)
        print("")
        print("Done.")
        print("")
        self.u.grab("Press [enter] to return to the menu...")

    def main(self):
        self.u.resize(80, 24)
        language = get_system_language()
        self.u.head("USBMap")
        print("")
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        print("Current Controllers:")
        print("")
        needs_rename = []
        rhub_paths   = []
        c_check      = [x for x in self.connected_controllers if not self.connected_controllers[x].get("is_hub",False)]
        if not len(c_check): print(" - {}None{}".format(self.rs,self.ce))
        else:
            # We have controllers - let's show them
            pad = max(len(self.connected_controllers[x]["parent"]) for x in c_check)
            names = [self.connected_controllers[x]["parent_name"] for x in c_check]
            for x in c_check:
                if "locationid" in self.connected_controllers[x]: continue # don't show hubs in this list
                acpi = self.get_safe_acpi_path(self.connected_controllers[x].get("acpi_path",None))
                name = self.connected_controllers[x]["parent_name"]
                par  = self.connected_controllers[x]["parent"]
                if name in self.illegal_names:
                    needs_rename.append(x)
                    self.controllers.pop(x,None) # Remove it from the controllers to map
                    print(" - {}{}{} @ {} ({}{}{})".format(self.rs,par.rjust(pad),self.ce,acpi if acpi else "Unknown ACPI Path",self.rs,"Needs Rename" if name in self.illegal_names else "Not Unique",self.ce))
                    continue
                print(" - {}{}{} @ {}".format(self.cs,par.rjust(pad),self.ce,acpi if acpi else "Unknown ACPI Path"))
                if not "XHCI" in self.connected_controllers[x]["type"]:
                    continue # Only check legally named XHCI controllers for RHUB paths
                # Get the RHUB name - mirrors the controller name if actually "RHUB"
                if acpi:
                    rhub_name = "RHUB" if x.split("@")[0].upper() == self.connected_controllers[x]["parent_name"] else x.split("@")[0].upper()
                    rhub_path = ".".join([acpi,rhub_name])
                    rhub_paths.append(rhub_path)
                    print("  \\-> {}RHUB{} @ {}".format(self.bs,self.ce,rhub_path))
        print("")
        print("{}D. Discover Ports{}{}".format(
            self.rs if needs_rename else "",
            " (Will Ignore Invalid Controllers)" if needs_rename else "",
            self.ce
        ))
        print("{}P. Edit & Create USBMap.kext{}{}".format(
            "" if self.merged_list else self.rs,
            "" if self.merged_list else " (Must Discover Ports First)",
            self.ce
        ))
        print("{}K. Create USBMapDummy.kext{}{}".format(
            "" if self.merged_list else self.rs,
            "" if self.merged_list else " (Must Discover Ports First)",
            self.ce
        ))
        print("R. Reset All Detected Ports")
        if os.path.exists(self.usb_list):
            print("B. Backup Detected Port Plist")
        if needs_rename:
            print("A. Generate ACPI Renames For Conflicting Controllers")
            print("L. Generate Plist Renames For Conflicting Controllers")
        if rhub_paths:
            print("H. Generate ACPI To Reset RHUBs ({}May Conflict With Existing SSDT-USB-Reset.aml!{})".format(self.rs,self.ce))
        print("")
        print("Q. Quit")
        print("")
        menu = self.u.grab("Please select an option:  ")
        if not len(menu):
            return
        if menu.lower() == "q":
            self.u.resize(80, 24)
            self.u.custom_quit()
        if menu.lower() == "k" and self.merged_list:
            self.build_kext(modern=True,legacy=True,dummy=True,padded_to=26)
        elif menu.lower() == "r":
            try:
                # Reset the merged_list and repopulate the controllers
                self.merged_list = OrderedDict()
                if os.path.exists(self.usb_list):
                    os.remove(self.usb_list)
            except Exception as e:
                print("Failed to remove USB.plist! {}".format(e))
            return
        elif menu.lower() == "b" and os.path.exists(self.usb_list):
            if not os.path.exists(self.output): os.mkdir(self.output)
            output = os.path.join(self.output,"USB-{}.plist".format(datetime.now().strftime("%Y-%m-%d %H.%M")))
            try: shutil.copyfile(self.usb_list,output)
            except: pass
            if os.path.exists(output): self.re.reveal(output,True)
        elif menu.lower() == "d":
            if not len(self.controllers):
                self.u.head("No Valid Controllers")
                print("")
                print("No valid controllers found for port discovery!")
                print("You may need plist/ACPI renames in order to discover.")
                print("")
                return self.u.grab("Press [enter] to return...")
            self.discover_ports()
        elif menu.lower() == "p" and self.merged_list:
            self.edit_plist()
        elif menu.lower() == "a" and needs_rename:
            self.generate_acpi_renames(needs_rename)
        elif menu.lower() == "l" and needs_rename:
            self.generate_renames(needs_rename)
        elif menu.lower() == "h" and rhub_paths:
            self.reset_rhubs(rhub_paths)

    # ... (todo o código anterior permanece inalterado) ...

    # Remova a definição da função main() daqui

if __name__ == '__main__':
    u = USBMap()
    while True:
        u.main()
        u.u.resize(80, 24)
        language = get_system_language()
        u.u.head(translate("USBMap", language))
        print("")
        u.u.grab(translate("Pressione [enter] para continuar...", language)) # ISSO AQUI É NOVO
        print(translate("Current Controllers:", language))
        print("")
        needs_rename = []
        rhub_paths = []
        c_check = [x for x in u.connected_controllers if not u.connected_controllers[x].get("is_hub", False)]
        if not len(c_check):
            print(f" - {u.rs}None{u.ce}")
        else:
            pad = max(len(u.connected_controllers[x]["parent"]) for x in c_check)
            names = [u.connected_controllers[x]["parent_name"] for x in c_check]
            for x in c_check:
                if "locationid" in u.connected_controllers[x]:
                    continue
                acpi = u.get_safe_acpi_path(u.connected_controllers[x].get("acpi_path", None))
                name = u.connected_controllers[x]["parent_name"]
                par = u.connected_controllers[x]["parent"]
                if name in u.illegal_names:
                    needs_rename.append(x)
                    u.controllers.pop(x, None)
                    print(" - {}{}{} @ {} ({}{}{})".format(u.rs, par.rjust(pad), u.ce, acpi if acpi else "Unknown ACPI Path",
                                                          u.rs, "Needs Rename" if name in u.illegal_names else "Not Unique",
                                                          u.ce))
                    continue
                print(" - {}{}{} @ {}".format(u.cs, par.rjust(pad), u.ce, acpi if acpi else "Unknown ACPI Path"))
                if not "XHCI" in u.connected_controllers[x]["type"]:
                    continue
                if acpi:
                    rhub_name = "RHUB" if x.split("@")[0].upper() == u.connected_controllers[x]["parent_name"] else \
                    x.split("@")[0].upper()
                    rhub_path = ".".join([acpi, rhub_name])
                    rhub_paths.append(rhub_path)
                    print("  \\-> {}RHUB{} @ {}".format(u.bs, u.ce, rhub_path))
        print("")
        print("{}D. Discover Ports{}{}".format(
            u.rs if needs_rename else "",
            " (Will Ignore Invalid Controllers)" if needs_rename else "",
            u.ce
        ))
        print("{}P. Edit & Create USBMap.kext{}{}".format(
            "" if u.merged_list else u.rs,
            "" if u.merged_list else " (Must Discover Ports First)",
            u.ce
        ))
        print("{}K. Create USBMapDummy.kext{}{}".format(
            "" if u.merged_list else u.rs,
            "" if u.merged_list else " (Must Discover Ports First)",
            u.ce
        ))
        print("R. Reset All Detected Ports")
        if os.path.exists(u.usb_list):
            print("B. Backup Detected Port Plist")
        if needs_rename:
            print("A. Generate ACPI Renames For Conflicting Controllers")
            print("L. Generate Plist Renames For Conflicting Controllers")
        if rhub_paths:
            print(
                "H. Generate ACPI To Reset RHUBs ({}May Conflict With Existing SSDT-USB-Reset.aml!{})".format(u.rs, u.ce))
        print("")
        print("Q. Quit")
        print("")
        menu = u.u.grab(translate("Please select an option: ", language))
        if not len(menu):
            continue
        if menu.lower() == "q":
            u.u.resize(80, 24)
            u.u.custom_quit()
        if menu.lower() == "k" and u.merged_list:
            u.build_kext(modern=True, legacy=True, dummy=True, padded_to=26)
        elif menu.lower() == "r":
            try:
                u.merged_list = OrderedDict()
                if os.path.exists(u.usb_list):
                    os.remove(u.usb_list)
            except Exception as e:
                print(f"Failed to remove USB.plist: {e}")
            
        elif menu.lower() == "b" and os.path.exists(u.usb_list):
            if not os.path.exists(u.output):
                os.mkdir(u.output)
            output = os.path.join(
                u.output,
                f"USB-{datetime.now().strftime('%Y-%m-%d %H.%M')}.plist",
            )
            try:
                shutil.copyfile(u.usb_list, output)
            except:
                pass
            if os.path.exists(output):
                u.re.reveal(output, True)
        elif menu.lower() == "d":
            if not len(u.controllers):
                u.u.head("No Valid Controllers")
                print("")
                print("No valid controllers found for port discovery!")
                print("You may need plist/ACPI renames in order to discover.")
                print("")
                u.u.grab(translate("Press [enter] to return to the menu...", language))
                u.discover_ports()
        elif menu.lower() == "p" and u.merged_list:
            u.edit_plist()
        elif menu.lower() == "a" and needs_rename:
            u.generate_acpi_renames(needs_rename)
        elif menu.lower() == "l" and needs_rename:
            u.generate_renames(needs_rename)
        elif menu.lower() == "h" and rhub_paths:
            u.reset_rhubs(rhub_paths)
    

        
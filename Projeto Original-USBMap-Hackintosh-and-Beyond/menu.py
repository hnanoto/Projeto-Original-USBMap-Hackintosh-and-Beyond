# menu.py
import os
from utils_translation import translate

def display_main_menu(u, needs_rename, merged_list, os_version, language):  # Adicionado o argumento 'language'
    u.u.resize(80, 24)
    u.u.head(translate("USBMap", language))  # Traduzindo o cabeçalho
    print("")
    print(translate("Current Controllers:", language))  # Traduzindo a mensagem
    print("")
    c_check = [x for x in u.connected_controllers if not u.connected_controllers[x].get("is_hub", False)]
    if not len(c_check):
        print(f" - {u.rs}None{u.ce}")
    else:
        pad = max(len(u.connected_controllers[x]["parent"]) for x in c_check)
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
    print(translate("R. Reset All Detected Ports", language))  # Traduzindo a mensagem
    if os.path.exists(u.usb_list):
        print(translate("B. Backup Detected Port Plist", language))  # Traduzindo a mensagem
    if needs_rename:
        print(translate("A. Generate ACPI Renames For Conflicting Controllers", language))  # Traduzindo a mensagem
        print(translate("L. Generate Plist Renames For Conflicting Controllers", language))  # Traduzindo a mensagem
    if rhub_paths:
        print(translate("H. Generate ACPI To Reset RHUBs (May Conflict With Existing SSDT-USB-Reset.aml!)", language))  # Traduzindo a mensagem
    print("")
    print(translate("Q. Quit", language))  # Traduzindo a mensagem
    print("")
    return u.u.grab(translate("Please select an option: ", language))  # Traduzindo a mensagem
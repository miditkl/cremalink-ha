# <img src="icon.png" alt="Cremalink Logo" height="45" style="vertical-align: middle; margin-right: 10px;"> cremalink for Home Assistant

**The official Home Assistant integration for monitoring and controlling IoT coffee machines via Cremalink.**

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fmiditkl%2Fcremalink-ha)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&repository=cremalink-ha&owner=miditkl)
[![License](https://img.shields.io/github/license/miditkl/cremalink-ha?style=for-the-badge&color=success)](LICENSE)
[![Source Code](https://img.shields.io/badge/Source-GitHub-black?style=for-the-badge&logo=github)](https://github.com/miditkl/cremalink-ha)

---

## ✨ Overview

This integration connects your Home Assistant instance to the **Cremalink** ecosystem, allowing for real-time state monitoring and control of smart coffee machines. It is designed to work in tandem with the **Cremalink Server Add-on**.

> [!NOTE] 
> This project was developed with a result-oriented approach, primarily optimized for the **De'Longhi PrimaDonna Soul**. While the architecture is designed to be extensible, some logic may currently be tightly coupled to this specific model.
>
> The goal is to make the library fully generic. If you encounter issues with other machines, contributions are highly encouraged!

> [!NOTE]
> **cremalink-ha** acts solely as a bridge to Home Assistant. Device management (e.g., adding new machines) is handled exclusively via the main **[cremalink](https://github.com/miditkl/cremalink)** project. Please set up your devices there before using this integration.
---

## 🚀 Installation

### 1. Install the Add-on (Required only for local connection)

Before installing this integration, you must install and configure the **Cremalink Server Add-on**. This add-on acts as the bridge between your coffee machine and Home Assistant.

👉 **[Go to Add-on Documentation](addons/cremalink-server/README.md)** for setup instructions.

### 2. Install the Integration

**Via HACS (Recommended):**
1.  Click the "Open your Home Assistant instance" badge above, or manually add this repository to HACS as a custom repository.
2.  Search for "Cremalink" and install.
3.  Restart Home Assistant.

**Manual Installation:**
1.  Copy the `custom_components/cremalink_ha` folder to your `config/custom_components/` directory.
2.  Restart Home Assistant.

---

## ⚙️ Configuration

1.  Navigate to **Settings** > **Devices & Services**.
2.  Click **Add Integration**.
3.  Search for **Cremalink**.
4.  Follow the configuration flow. [You will need to provide the connection details for the Cremalink Server Add-on.](https://github.com/miditkl/cremalink-ha/discussions/5)

---

## 🤝 Contributing

Contributions are welcome! If you have a machine profile not yet supported, please check the [Project Wiki of the official cremalink repository](https://github.com/miditkl/cremalink/wiki/) on how to add new definitions.

---

## 📄 License

Distributed under the **AGPL-3.0-or-later** License. See `LICENSE` for more information.

---

*Developed by [Midian Tekle Elfu](mailto:developer@midian.tekleelfu.de). Supported by the community.*

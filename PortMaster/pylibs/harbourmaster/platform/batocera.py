# SPDX-License-Identifier: MIT
#
# Batocera, REG-Linux and Knulli.

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from loguru import logger
from .base import PlatformBase


class PlatformBatocera(PlatformBase):
    MOVE_PM_BASH = False
    ES_NAME = "batocera-es"

    BATOCERA_CONFIG_FILES = [
        "/userdata/system/knulli.conf",   # Knulli
        "/userdata/system/system.conf",   # REG-Linux, maybe?
        "/userdata/system/batocera.conf", # Batocera, Knulli
        ]
    BATOCERA_CONFIG = None

    def portmaster_install(self, bash_files):
        super().portmaster_install(bash_files)
        """
        Just move PortMaster.sh from `PortMaster/` to `/userdata/roms/ports/`.
        """

        PM_LOCATION   = self.hm.tools_dir   / "PortMaster" / "PortMaster.sh"
        BAD_LOCATION  = self.hm.tools_dir   / "PortMaster.sh"
        GOOD_LOCATION = self.hm.scripts_dir / "PortMaster.sh"

        try:
            if PM_LOCATION.is_file():
                shutil.copy2(PM_LOCATION, GOOD_LOCATION)
                PM_LOCATION.unlink()

            # Delete this file so we don't trigger the `post_install` action below.
            if BAD_LOCATION.is_file():
                BAD_LOCATION.unlink()

        except OSError as e:
            logger.error(f"Error during file operation: {e}")

    def portmaster_post_install(self):
        super().portmaster_post_install()
        """
        Old installs use `MOVE_PM_BASH`, so it will move the PortMaster.sh to `BAD_LOCATION`
        and the above `portmaster_install` code will not have been run, this means that we need to move
        `BAD_LOCATION` to `GOOD_LOCATION`.

        On newer/future updates this won't matter as PortMaster.sh should not be present at `BAD_LOCATION`.
        """
        BAD_LOCATION  = self.hm.tools_dir   / "PortMaster.sh"
        GOOD_LOCATION = self.hm.scripts_dir / "PortMaster.sh"

        try:
            if BAD_LOCATION.is_file():
                shutil.copy2(BAD_LOCATION, GOOD_LOCATION)
                BAD_LOCATION.unlink()
        except OSError as e:
            logger.error(f"Error during file operation: {e}")

    """
    Taken from Mikhailzrick's getInvertButtonsValue
    https://github.com/Mikhailzrick/batocera.linux/blob/43930d59a682953049c90833175c710f8f6fc018/package/batocera/core/batocera-configgen/configgen/configgen/generators/libretro/libretroConfig.py#L24
    """
    # Return value for es invertedbuttons
    def get_invert_buttons_value(self):  
        ES_SETTINGS = Path('/userdata/system/configs/emulationstation/es_settings.cfg')

        if not ES_SETTINGS.is_file():
            return False

        tree = ET.parse(str(ES_SETTINGS))

        root = tree.getroot()
        # Find the InvertButtons element and return value
        elem = root.find(".//bool[@name='InvertButtons']")

        if elem is not None:
            return elem.get('value') == 'true'

        return False  # Return False if not found 

    def batocera_settings_get(self, key, default=None):
        """
        This parses the batocera_settings files.
        """
        if self.BATOCERA_CONFIG is None:
            for config_file in self.BATOCERA_CONFIG_FILES:
                if Path(config_file).is_file():
                    self.BATOCERA_CONFIG = config_file
                    break
            else:
                self.BATOCERA_CONFIG = ""
                logger.error(f"Unable to find a suitable batocera.conf file, returning {default}")
                return default

        if self.BATOCERA_CONFIG == "":
            # Return default every time since none was found.
            return default

        with open(self.BATOCERA_CONFIG, 'r') as fh:
            for line in fh:
                line = line.strip()

                # Blank lines
                if line == '':
                    continue

                # Comments
                if line.startswith('#'):
                    continue

                # I dunno, lets just skip it.
                if '=' not in line:
                    continue

                line_key, line_value = line.split('=', 1)
                if key != line_key.strip():
                    continue

                logger.debug(f"{key}={line_value}")
                return line_value.strip()

        logger.debug(f"{key}={default} (default)")
        return default

    def loaded(self):
        self.WANT_SWAP_BUTTONS = not self.get_invert_buttons_value()
        # if self.WANT_SWAP_BUTTONS:
            # self.WANT_XBOX_FIX = not self.WANT_XBOX_FIX

    def gamelist_file(self):
        return self.hm.ports_dir / 'gamelist.xml'

    def first_run(self):
        self.portmaster_install([])

        REBOOT_FILE = self.hm.tools_dir / ".pugwash-reboot"
        REBOOT_FILE.touch()

    def portmaster_install(self, bash_files):
        """
        Move files into place.
        """
        super().portmaster_install(bash_files)

        TL_DIR = self.hm.tools_dir / "PortMaster"
        BC_DIR = TL_DIR / "batocera"

        # ACTIVATE THE CONTROL
        logger.debug(f'Copy {BC_DIR / "control.txt"} -> {TL_DIR / "control.txt"}')
        shutil.copy(BC_DIR / "control.txt", TL_DIR / "control.txt")

        TASK_SET = TL_DIR / "tasksetter"
        if TASK_SET.is_file():
            TASK_SET.unlink()

        TASK_SET.touch()


class PlatformREGLinux(PlatformBatocera):
    ...


class PlatformKnulli(PlatformBatocera):
    WANT_XBOX_FIX = True

    def loaded(self):
        want_swap = self.batocera_settings_get('ports["PortMaster.sh"].xbox_layout', None)

        if want_swap is None:
            want_swap = self.batocera_settings_get('ports.xbox_layout', None)

        if want_swap is not None:
            self.WANT_XBOX_FIX = False
            self.WANT_SWAP_BUTTONS = want_swap == "0"

        else:
            self.WANT_SWAP_BUTTONS = not self.get_invert_buttons_value()

            if self.WANT_SWAP_BUTTONS:
                self.WANT_XBOX_FIX = not self.WANT_XBOX_FIX

    def portmaster_install(self, bash_files):
        """
        Move files into place.
        """
        super().portmaster_install(bash_files)

        TL_DIR = self.hm.tools_dir / "PortMaster"
        BC_DIR = TL_DIR / "knulli"

        # ACTIVATE THE CONTROL
        logger.debug(f'Copy {BC_DIR / "control.txt"} -> {TL_DIR / "control.txt"}')
        shutil.copy(BC_DIR / "control.txt", TL_DIR / "control.txt")

        TASK_SET = TL_DIR / "tasksetter"
        if TASK_SET.is_file():
            TASK_SET.unlink()

        TASK_SET.touch()

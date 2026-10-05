# SPDX-License-Identifier: MIT
#
# Sources that read GitHub releases / repositories.

import datetime
import json
from gettext import gettext as _
from loguru import logger
from ..info import port_info_load, port_info_merge
from ..util import name_cleaner
from ..util import net
from .base import BaseSource


class GitHubRawReleaseV1(BaseSource):
    VERSION = 4

    def load(self):
        self._data = self._config.setdefault('data', {}).setdefault('data', {})
        self.ports = self._config.setdefault('data', {}).setdefault('ports', [])
        self.utils = self._config.setdefault('data', {}).setdefault('utils', [])
        self._load()
        self._load_images()

    def save(self):
        with self._file_name.open('w') as fh:
            json.dump(self._config, fh, indent=4)

    def _load_images(self):
        self.images = {}
        all_ports = set(self.ports)
        seen_ports = set()

        for file_name in self._images_dir.iterdir():
            if file_name.suffix.casefold() not in ('.jpg', '.png'):
                continue

            if file_name.name.count('.') < 2:
                continue

            port_name, image_type, image_suffix = file_name.name.casefold().rsplit('.', 2)
            port_name = self.clean_name(port_name + '.zip')

            if port_name not in all_ports:
                logger.warning(f"Port image {port_name} - {image_type} for unknown port.")
            elif image_type == 'screenshot':
                seen_ports.add(port_name)

            self.images.setdefault(self.clean_name(port_name), {})[image_type] = file_name.name

        for port_name in (all_ports - seen_ports):
            logger.warning(f"Port image {port_name}: missing.")

    def _load(self):
        """
        Overload to add additional loading.
        """
        ...

    def _update(self):
        """
        Overload to add additional updating.
        """
        ...

    def _clear(self):
        """
        Overload to add additional clearing.
        """
        ...

    def update(self):
        # cprint(f"<b>{self._config['name']}</b>: updating")
        if self.hm.callback is not None:
            self.hm.callback.message(" - {}".format(_("Updating")))

        # Scrap the rest
        self._clear()
        self._data = {}
        self.ports = []
        self.utils = []
        self.images = {}

        if self._did_update:
            # cprint(f"- <b>{self._config['name']}</b>: up to date already.")
            self.hm.callback.message(" - {}".format(_("Up to date already")))
            return

        # cprint(f"- <b>{self._config['name']}</b>: Fetching latest ports")
        if self.hm.callback is not None:
            self.hm.callback.message("  - {}".format(_("Fetching latest info")))

        data = net.fetch_json(self._config['url'])
        if data is None:
            return

        ## Load data from the assets.
        for asset in data['assets']:
            result = {
                'name': asset['name'],
                'size': asset['size'],
                'url': asset['browser_download_url'],
                }

            self._data[self.clean_name(asset['name'])] = result

            if asset['name'].lower().endswith('.squashfs'):
                self.utils.append(self.clean_name(asset['name']))

        self._update()

        self._load_images()

        self._config['version'] = self.VERSION

        self._config['data']['ports'] = self.ports
        self._config['data']['utils'] = self.utils
        self._config['data']['data']  = self._data

        self._config['last_checked'] = datetime.datetime.now().isoformat()

        self.save()
        self._did_update = True
        # cprint(f"- <b>{self._config['name']}:</b> Done.")
        self.hm.callback.message("  - {}".format(_("Done.")))

    def download(self, port_name, temp_dir=None, md5_result=None):
        if md5_result is None:
            md5_result = [None]

        if port_name not in self._data:
            logger.error(f"Unable to find port {port_name}")
            self.hm.callback.message_box(_("Unable to find {port_name}.").format(port_name=port_name))
            return None

        if temp_dir is None:
            temp_dir = self.hm.temp_dir

        if (port_name + '.md5') in self._data:
            md5_file = port_name + '.md5'
        elif (port_name + '.md5sum') in self._data:
            md5_file = port_name + '.md5sum'
        else:
            self.hm.callback.message_box(_("Unable to find verification info for {port_name}.").format(port_name=port_name))
            logger.error(f"Unable to find md5 for {port_name}")
            return None

        md5_source = net.fetch_text(self._data[md5_file]['url'])
        if md5_source is None:
            logger.error(f"Unable to download md5 file: {self._data[md5_file]['url']!r}")
            self.hm.callback.message_box(_("Unable to download verification info for {port_name}.").format(port_name=port_name))
            return None

        md5_source = md5_source.strip().split(' ', 1)[0]

        zip_file = net.download(temp_dir / port_name, self._data[port_name]['url'], md5_source, callback=self.hm.callback)

        if zip_file is not None:
            # cprint("<b,g,>Success!</b,g,>")

            self.hm.callback.message("  - {}".format(_("Success!")))

        md5_result[0] = md5_source

        return zip_file

    def port_info(self, port_name):
        port_name = self.clean_name(port_name)

        if port_name not in getattr(self, '_info', {}):
            return {}

        return self._info[port_name]

    def port_download_size(self, port_name, check_runtime=True):
        port_name = self.clean_name(port_name)

        if port_name not in getattr(self, '_data', {}):
            return 0

        size = self._data[port_name]['size']

        if check_runtime and port_name in getattr(self, '_info', {}):
            port_info = self._info[port_name]

            if len(port_info['attr'].get('runtime', [])) > 0:
                for runtime in port_info['attr']['runtime']:
                    runtime_file = (self.hm.libs_dir / runtime)
                    if not runtime_file.exists():
                        size += self.hm.port_download_size(runtime)

        return size

    def port_download_url(self, port_name):
        port_name = self.clean_name(port_name)

        if port_name not in getattr(self, '_data', {}):
            return None

        return self._data[port_name]['url']


class GitHubRepoV1(GitHubRawReleaseV1):
    VERSION = 2

    def _load(self):
        """
        Overload to add additional loading.
        """
        self._info = self._config.setdefault('data', {}).setdefault('info', {})

    def update(self):
        # cprint(f"<b>{self._config['name']}</b>: updating")
        if self._did_update:
            # cprint(f"- <b>{self._config['name']}</b>: up to date already.")
            return

        self._clear()
        self._data = {}
        self._info = {}
        self.ports = []
        self.utils = []

        user_name = self._config['config']['user_name']
        repo_name = self._config['config']['repo_name']
        branch_name = self._config['config']['branch_name']
        sub_folder = self._config['config']['sub_folder']

        git_url = f"https://api.github.com/repos/{user_name}/{repo_name}/git/trees/{branch_name}?recursive=true"

        # cprint(f"- <b>{self._config['name']}</b>: Fetching latest ports")
        self.hm.callback.message("  - {}".format(_("{source_name}: Fetching latest ports").format(source_name=self._config['name'])))

        git_info = net.fetch_json(git_url)
        if git_info is None:
            return None

        ports_json_file = None

        for item in git_info['tree']:
            path = item["path"]
            if not path.startswith(sub_folder):
                continue

            name = path.rsplit('/', 1)[1]

            if not (path.endswith('.zip') or
                    path.endswith('.md5') or
                    path.endswith('.squashfs') or
                    path.endswith('.md5sum') or
                    name == 'ports.json'):
                continue

            result = {
                'name': name,
                'size': item['size'],
                'url': f"https://github.com/{user_name}/{repo_name}/raw/{branch_name}/{path}",
                }

            name = self.clean_name(name)
            self._data[name] = result

            if name.endswith('.squashfs'):
                self.utils.append(self.clean_name(asset['name']))

            if name == 'ports.json':
                ports_json_file = name

        if ports_json_file is not None:
            # cprint(f"- <b>{self._config['name']}:</b> Fetching info.")
            self.hm.callback.message("  - {}".format(_("Fetching info.")))
            ports_json = net.fetch_json(self._data[ports_json_file]['url'])

            for port_info in ports_json['ports']:
                port_name = port_info['name']

                port_name = self.clean_name(port_name)

                # Clean it up.
                self._info[port_name] = port_info_load(port_info)

                self.ports.append(port_name)

        self._config['version'] = self.VERSION

        self._config['data']['ports'] = self.ports
        self._config['data']['utils'] = self.utils
        self._config['data']['data']  = self._data
        self._config['data']['info']  = self._info

        self._config['last_checked'] = datetime.datetime.now().isoformat()

        self.save()
        self._did_update = True
        # cprint(f"- <b>{self._config['name']}:</b> Done.")
        self.hm.callback.message(f"  - Done.")


    def download(self, port_name, temp_dir=None, md5_result=None):
        if md5_result is None:
            md5_result = [None]

        zip_file = super().download(port_name, temp_dir, md5_result)

        if zip_file is None:
            return None

        if port_name in self.utils:
            ## Utils
            return zip_file

        zip_info = port_info_load({})

        zip_info['name'] = name_cleaner(port_name)
        zip_info['status'] = {
            'source': self._config['name'],
            'md5':    md5_result[0],
            'status': 'downloaded',
            }
        zip_info['zip_file'] = zip_file

        port_info = self.port_info(port_name)
        port_info_merge(zip_info, port_info)

        return zip_info

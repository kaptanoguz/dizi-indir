from .plugins.dizibox import DiziboxPlugin
from .plugins.hdf import HDFPlugin

class DiziboxEngine:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.plugins = {
            'dizibox': DiziboxPlugin(socketio),
            'hdfilmcehennemi': HDFPlugin(socketio)
        }

    def get_plugin(self, url):
        if 'dizibox' in url:
            return self.plugins['dizibox']
        elif 'hdfilmcehennemi' in url:
            return self.plugins['hdfilmcehennemi']
        return None

    def get_season_links(self, url):
        plugin = self.get_plugin(url)
        if plugin and hasattr(plugin, 'get_season_links'):
            return plugin.get_season_links(url)
        return [url]

    def get_episode_info(self, url):
        plugin = self.get_plugin(url)
        if plugin:
            return plugin.get_info(url)
        return None

    def download_episode(self, info, download_id):
        url = info.get('url', '')
        plugin = self.get_plugin(url)
        if plugin:
            return plugin.download(info, download_id)
        return False

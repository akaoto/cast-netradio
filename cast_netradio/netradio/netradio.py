import subprocess
import os
import requests
import re
import mimetypes

smart_phone_user_agent = 'Mozilla/5.0 (Linux; U; Android 2.2.1; en-us; '
smart_phone_user_agent += 'Nexus One Build/FRG83) AppleWebKit/533.1 '
smart_phone_user_agent += '(KHTML, like Gecko) Version/4.0 Mobile Safari/533.1'


class NetRadio(object):

    def __init__(self, dirs, fname):
        super().__init__()
        self._base_path = os.path.join('dl', *dirs)
        if not os.path.exists(self._base_path):
            os.makedirs(self._base_path)
        self._file_path = os.path.join('dl', *dirs, fname)

    @property
    def file_path(self):
        return self._file_path

    @property
    def content_type(self):
        return mimetypes.guess_type(self._file_path)[0]

    def download_method(self, fname):
        raise NotImplementedError

    def download(self):
        if os.path.exists(self._file_path):
            print(self._file_path, 'already exists.')
        else:
            print('Download', self._file_path)
            self.download_method(self._file_path)
        return self._file_path


class Lantis(NetRadio):

    def __init__(self, url):
        m = re.match('https://lantis-net.com/(.+)/?', url)
        if not m:
            raise Exception('Wrong URL')
        radio_title = m.group(1)

        headers = {}
        headers['User-Agent'] = smart_phone_user_agent
        r = requests.get(url, headers=headers)
        m = re.search(r'"(http://.+/(.+\.mp3))"', r.text)
        if not m:
            raise Exception('Not found download URL')
        self._dl_url, fname = m.groups()

        super().__init__(['lantis', radio_title], fname)

    def download_method(self, fname):
        r = requests.get(self._dl_url, headers={
                         'User-Agent': smart_phone_user_agent})
        with open(fname, 'wb') as f:
            f.write(r.content)


class Hibiki(NetRadio):
    headers = {'X-Requested-With': 'XMLHttpRequest'}

    @classmethod
    def get_radio_programs(cls, day_of_week, limit, page):
        url = 'https://vcms-api.hibiki-radio.jp/api/v1/programs?'
        url += 'day_of_week={day_of_week}'
        url += '&limit={limit}&page={page}'
        r = requests.get(url.format(**locals()), headers=cls.headers)
        return r.json()

    @classmethod
    def get_info(cls, access_id):
        url = 'https://vcms-api.hibiki-radio.jp/api/v1/programs/{access_id}'
        r = requests.get(url.format(**locals()), headers=cls.headers)
        return r.json()

    @classmethod
    def get_playlist_url(cls, video_id):
        url = 'https://vcms-api.hibiki-radio.jp/api/v1/videos/play_check?'
        url += 'video_id={video_id}'
        r = requests.get(url.format(**locals()), headers=cls.headers)
        playlist_url = r.json()['playlist_url']
        return playlist_url

    def __init__(self, url):
        m = re.match(r'https://hibiki-radio\.jp/description/(.+)/detail', url)
        if not m:
            raise Exception('Wrong URL')
        access_id = m.group(1)
        info = self.get_info(access_id)
        self._video_id = info['episode']['video']['id']
        episode_name = info['latest_episode_name']
        fname = episode_name + '.aac'

        super().__init__(['hibiki', access_id], fname)

    def download_method(self, fname):
        playlist_url = self.get_playlist_url(self._video_id)
        popen = subprocess.Popen(['ffmpeg', '-i', playlist_url,
                                  '-vcodec', 'copy', '-acodec', 'copy',
                                  '-bsf:a', 'aac_adtstoasc', fname,
                                  '-y'])
        popen.wait()

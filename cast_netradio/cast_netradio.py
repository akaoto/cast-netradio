import requests
import bs4
from beebotte import BBT
import re
import netradio
import subprocess
import pychromecast
import time
import param


net_radio = {
    'lantis': {
        'regexp': r'https://lantis-net\.com/.+',
        'class': netradio.Lantis
    },
    'hibiki': {
        'regexp': r'https://hibiki-radio.jp/description/(.+)/detail',
        'class': netradio.Hibiki
    }
}


class NetRadioCast(object):

    def __init__(self):
        subprocess.Popen(['python', '-m', 'http.server'])
        self._cast = pychromecast.Chromecast(param.chromecast_ip)

    def run(self):
        checker = self._check_update()
        while True:
            time.sleep(1)
            radio_info = next(checker)
            if not radio_info:
                continue

            regexp = net_radio[radio_info[0]]['regexp']
            url = self._search_netradio_site(radio_info, regexp)
            if not url:
                continue

            try:
                cl = net_radio[radio_info[0]]['class']
            except Exception:
                raise Exception('Unknown error occured')

            downloader = cl(url)
            downloader.download()
            file_path = 'http://{server_ip}:8000/'.format(**globals())
            file_path += '{downloader.file_path}'.format(**locals())
            print('Start to play media')
            self._cast.media_controller.play_media(
                file_path, downloader.content_type)

    def _check_update(self):
        bbt = BBT(token=param.bbt_token, hostname=param.bbt_hostname)
        records = bbt.read(param.bbt_channel, param.bbt_resource, limit=1)[0]
        while True:
            new_records = bbt.read(
                param.bbt_channel, param.bbt_resource, limit=1)[0]
            if records == new_records:
                yield None
                continue
            records = new_records
            yield records['data']

    def _search_netradio_site(self, radio_info, regexp):
        req = requests.get('http://google.com/search?q=ラジオ+' +
                           '+'.join(radio_info))
        soup = bs4.BeautifulSoup(req.text, 'html.parser')
        anchors = soup.select('.r a')
        cand_url = []
        for anchor in anchors:
            url = anchor.get('href')
            r = r'/url\?q=({regexp})&sa=.+'.format(**locals())
            m = re.match(r, url)
            if m:
                return m.group(1)


nrc = NetRadioCast()
nrc.run()

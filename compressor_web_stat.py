#!/usr/bin/env python3
# -*- coding: utf-8 -*
"""Collects data from Atlas Copco GA90VP_16 compressors and saves it to InfluxDB for subsequent processing in Grafana"""

import logging
from pathlib import Path
from requests import session
from requests.exceptions import ConnectionError
from datetime import datetime
import pytz
from util.influxdb_helper import InfluxDBHelper

_DEBUG_ON = False
_P_TIMEZONE = pytz.timezone('Asia/Magadan')
_PRG_DIR = Path(__file__).parent.absolute()
_REP_DIR = _PRG_DIR / 'reports'
_LOG_FILE = _PRG_DIR / 'compressors.log'
_P_TIMEZONE = pytz.timezone('Asia/Magadan')
_IP_INFLUXDB = '10.100.59.108'
log_format = f"%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
logging.basicConfig(handlers=(logging.FileHandler(_LOG_FILE), logging.StreamHandler()),
                    level=logging.DEBUG if _DEBUG_ON else logging.INFO, format=log_format)

logger = logging.getLogger()
# List of compressors (last digit is type: 1 - old; 2 - new, differ in request and received data)
_COMPRESSORS = [
    ['10.100.58.30', '080BL515', 'Compressor Room', 1],
    ['10.100.58.31', '080BL516', 'Compressor Room', 1],
    ['10.100.58.32', '350BL907', 'Compressor Room', 1],
    ['10.100.58.33', '350BL908', 'Compressor Room', 1],
    ['10.100.58.34', '080BL517', 'Compressor Room', 2],
    ['10.100.58.35', '080BL755', 'Compressor Room', 1],
    ['10.100.58.36', '900CP110', 'Compressor Room', 1],
]

_TIMEOUT = 2
_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Length': '603',
            'Cookie': 'LangName=English',
            'Connection': 'keep-alive'
            }
# Post requests to compressor. _PAYLOAD1 - "old compressors"; _PAYLOAD2 - "new"
_PAYLOAD1 = 'QUESTION=30020130020330020530030130030230030430030a30070130070330070430070530070630070730070830070930070b30070c30070d30071830210130210530210a300501300504300505300507300508300509300e03300e04300e2a300e8831130131130331130431130531130731130831130931130a31130b31130c31130d31130e31130f31131031131131131231131331131431131531131631131731131831131931131a31131b31131c31131d31131e31131f31132031132131132231132331132431132531132631132731132831132931132a31132b31132c31140131140231140331140431140531140631140731140831140931140a31140b31140c31140d31140e31140f311410311411311412300901300906300911300907300912300909300108'
_PAYLOAD2 = 'QUESTION=30020830020930020a30020c30020e30021030030130030230030430030530030630030730030a30070130070230070330070430070530070630070730070830070930070b30070c30070d30070e30070f30071430071530071830072230072330072430072530072630072730210130210530210a300501300502300504300505300506300507300508300509300e03300e04300e2a31130131130331130431130531130731130831130931130a31130b31130c31130d31130e31130f31131031131131131231131331131431131531131631131731131831131931131a31131b31131c31131d31131e31131f31132031132131132231132331132431132531132631132731132831132931132a31132b31132c31132d31132e31132f31133031133131133231133331133431133531133631133731133831133931133a31133b31133c31133d31133e31133f31134031134131134231134331134431134531134631134731134831134931134a31134b31134c31134d31134e31134f31135031135131135231135331135431135531135631135731135831135931135a31135b31135c31135d31135e31135f31136031136131136231136331136431136531136631136731140131140231140331140431140531140631140731140831140931140a31140b31140c31140d31140e31140f311410311411311412300901300906300911300907300912300909300108'


def _hex2int(hex_val: str) -> int:
    return int.from_bytes(bytes.fromhex(hex_val), "big")


class CompressorGetDataError(Exception):
    pass


class Compressor(object):
    """HTTP data collection from compressor"""

    def __init__(self, host_ip='10.100.58.30', tag='080BL515', locate='Compressor Room', type=1):
        self.host_ip = host_ip
        self.tag = tag
        self.locate = locate
        self.type = type
        self.http_addr = "http://" + self.host_ip + "/cgi-bin/mkv.cgi"
        self.req = None
        self.http_payload = _PAYLOAD1 if self.type == 1 else _PAYLOAD2
        self.http_headers = _HEADERS
        self.timeout = _TIMEOUT
        self.data = {}
        self.raw_data = ''
        self.slice_raw_data = [0] * 99 if self.type == 1 else [0] * 176
        self.influxdb_body = []
        self.cnt_files = 0
        self.cnt_time = 0
        self.cnt_dl_size = 0
        self.dt = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._update()
        logger.debug(f"Init class Compressor, host_ip: {host_ip}")

    def _update(self):
        if self._get_raw_data():
            self._slice_raw_data()
            self._parse_data1() if self.type == 1 else self._parse_data2()
            self._mk_influxdb_body()

    def _get_raw_data(self):
        """Get data from compressor"""
        try:
            with session() as c:
                resp = c.post(self.http_addr,
                              headers=self.http_headers, data=self.http_payload, timeout=self.timeout)
                if not resp.ok:
                    err_msg = f"Can't get data from compressor. " \
                              f"Status code:{resp.status_code}; " \
                              f"Reason: {resp.status_code}. "
                    print(err_msg)
                    raise CompressorGetDataError(err_msg)
                self.raw_data = resp.text

        except (ConnectionError, CompressorGetDataError) as e:
            logger.error(e)
            return None
        return resp.ok

    def _slice_raw_data(self):
        """Size of each parameter data is 8 bytes, X - skipped parameter, replace with 8 Z characters"""
        pos = 0
        self.raw_data = self.raw_data.replace('X', 'ZZZZZZZZ')
        for i in range(len(self.slice_raw_data)):
            a = self.raw_data[i]
            self.slice_raw_data[i] = self.raw_data[pos:pos + 8]
            pos += 8

    def _parse_data1(self):
        """Old compressors"""
        self.data['AI'] = [
            ['Compressor Outlet', _hex2int(self.slice_raw_data[0][:4]) / 1000, 'bar'],
            ['Element Outlet', int(_hex2int(self.slice_raw_data[1][:4]) / 10), '°C'],
            ['Ambient Air', int(_hex2int(self.slice_raw_data[2][:4]) / 10), '°C']]

        # def _get_counters(self):
        self.data['CNT'] = [
            ['Running Hours', int(_hex2int(self.slice_raw_data[7][:8]) / 3600), 'hrs'],
            ['Motor Starts', _hex2int(self.slice_raw_data[8][:8]), ''],
            ['Load Relay', _hex2int(self.slice_raw_data[9][:8]), ''],
            ['Fan Starts', _hex2int(self.slice_raw_data[15][:8]), ''],
            ['Accumulated Volume', _hex2int(self.slice_raw_data[16][:8]) * 1000, ''],
            ['Module Hours', int(_hex2int(self.slice_raw_data[17][:8]) / 3600), 'hrs'],
            ['Low Load Hours', int(_hex2int(self.slice_raw_data[18][:8])
                                   if 'Z' not in self.slice_raw_data[18] else 0 / 3600), 'hrs'],
        ]
        self.data['VFD'] = [
            ['Rotate', int(_hex2int(self.slice_raw_data[19][:4])), 'rpm'],
            # ['Current', int(_hex2int(self.slice_raw_data[21][:4])), 'A'],
            ['Current', int(_hex2int(self.slice_raw_data[21][:4])) if 'Z' not in self.slice_raw_data[21] else '', 'A'],
            ['Flow', int(_hex2int(self.slice_raw_data[20][:8])), '%'],
        ]
        self.data['DI'] = [
            ['Emergency Stop', int(_hex2int(self.slice_raw_data[3][:4])), ''],
            ['Overload Fan Motor', int(_hex2int(self.slice_raw_data[4][:4])), ''],
            ['Electronic Condensate Drain', int(_hex2int(self.slice_raw_data[5][:4]) if 'Z' not in self.slice_raw_data[5] else '0'), ''],
            ['Pressure Setting Selection', int(_hex2int(self.slice_raw_data[6][:4])), ''],
        ]
        self.data['DO'] = [
            ['Fan Motor', int(_hex2int(self.slice_raw_data[22][:4])), ''],
            ['Blowoff', int(_hex2int(self.slice_raw_data[23][:4])), ''],
            ['General Shutdown', int(_hex2int(self.slice_raw_data[24][:4])), ''],
            ['Automatic Operation', int(_hex2int(self.slice_raw_data[25][:4])), ''],
            ['General Warning', int(_hex2int(self.slice_raw_data[26][:4])), ''],
            ['Run Enable Main Motor', int(_hex2int(self.slice_raw_data[27][:4])), ''],
        ]
        self.data['SP'] = [
            ['No Valid Pressure Control', int(_hex2int(self.slice_raw_data[28][4:8])), ''],
            ['Motor Converter 1 Alarm', int(_hex2int(self.slice_raw_data[29][4:8])), ''],
            ['Expansion Module Communication', int(_hex2int(self.slice_raw_data[30][4:8])), ''],
            # ['Low Load Alarm', int(_hex2int(self.slice_raw_data[31][4:8])), ''],
            ['Low Load Alarm', int(_hex2int(self.slice_raw_data[31][4:8]))
            if 'Z' not in self.slice_raw_data[31] else 0, ''],
        ]
        self.data['MS'] = [
            ['PrimaryState', int(_hex2int(self.slice_raw_data[98][4:8])), ''],
        ]

    def _parse_data2(self):
        """New compressors"""
        self.data['AI'] = [
            ['Controller Temperature', _hex2int(self.slice_raw_data[0][:4]) / 10, '°C'],
            ['Compressor Outlet', _hex2int(self.slice_raw_data[1][:4]) / 1000, 'bar'],
            ['Relative Humidity', _hex2int(self.slice_raw_data[2][:4]), '%'],
            ['Vessel Pressure', _hex2int(self.slice_raw_data[3][:4]) / 1000, 'bar'],
            ['Element Outlet', int(_hex2int(self.slice_raw_data[4][:4]) / 10), '°C'],
            ['Ambient Air', int(_hex2int(self.slice_raw_data[5][:4]) / 10), '°C']]
        # def _get_counters(self):
        self.data['CNT'] = [
            ['Running Hours', int(_hex2int(self.slice_raw_data[13][:8]) / 3600), 'hrs'],
            ['Loaded  Hours', int(_hex2int(self.slice_raw_data[14][:8]) / 3600), 'hrs'],
            ['Motor Starts', _hex2int(self.slice_raw_data[15][:8]), ''],
            ['Load Relay', _hex2int(self.slice_raw_data[16][:8]), ''],
            ['Fan Starts', _hex2int(self.slice_raw_data[22][:8]), ''],
            ['Accumulated Volume', _hex2int(self.slice_raw_data[23][:8]) * 1000, ''],
            ['Module Hours', int(_hex2int(self.slice_raw_data[24][:8]) / 3600), 'hrs'],
            ['Emergency Stops', int(_hex2int(self.slice_raw_data[25][:8])), ''],
            ['Direct Stops', int(_hex2int(self.slice_raw_data[26][:8])), ''],
        ]
        self.data['VFD'] = [
            ['Rotate', int(_hex2int(self.slice_raw_data[36][:4])), 'rpm'],
            # ['Current', int(_hex2int(self.slice_raw_data[21][:4])), 'A'],
            ['Current', int(_hex2int(self.slice_raw_data[38][:4])) if 'Z' not in self.slice_raw_data[21] else '', 'A'],
            ['Flow', int(_hex2int(self.slice_raw_data[37][:8])), '%'],
        ]
        self.data['DI'] = [
            ['Emergency Stop', int(_hex2int(self.slice_raw_data[6][:4])), ''],
            ['Overload Fan Motor', int(_hex2int(self.slice_raw_data[7][:4])), ''],
            ['Electronic Condensate Drain', int(_hex2int(self.slice_raw_data[8][:4])), ''],
            ['Active Power Supply', int(_hex2int(self.slice_raw_data[9][:4])), ''],
            ['Phase Sequence', int(_hex2int(self.slice_raw_data[10][:4])), ''],
            ['Air Filter', int(_hex2int(self.slice_raw_data[11][:4])), ''],
            ['Pressure Setting Selection', int(_hex2int(self.slice_raw_data[12][:4])), ''],
        ]
        self.data['DO'] = [
            ['Fan Motor', int(_hex2int(self.slice_raw_data[39][:4])), ''],
            ['Blowoff', int(_hex2int(self.slice_raw_data[40][:4])), ''],
            ['Run Enable Main Motor', int(_hex2int(self.slice_raw_data[41][:4])), ''],
            ['Recirculation Valve', int(_hex2int(self.slice_raw_data[42][:4])), ''],
            ['Cubicle Fan', int(_hex2int(self.slice_raw_data[43][:4])), ''],
            ['Automatic Operation', int(_hex2int(self.slice_raw_data[44][:4])), ''],
            ['General Warning', int(_hex2int(self.slice_raw_data[45][:4])), ''],
            ['General Shutdown', int(_hex2int(self.slice_raw_data[46][:4])), ''],
        ]
        self.data['SP'] = [
            ['No Valid Pressure Control', int(_hex2int(self.slice_raw_data[47][4:8])), ''],
            ['Motor Converter 1 Alarm', int(_hex2int(self.slice_raw_data[48][4:8])), ''],
            ['Expansion Module Communication', int(_hex2int(self.slice_raw_data[49][4:8])), ''],

        ]
        self.data['MS'] = [
            ['PrimaryState', int(_hex2int(self.slice_raw_data[175][4:8])), ''],
        ]

    def _mk_influxdb_body(self):
        """Forms a record block for InfluxDB in JSON """
        self.influxdb_body = []
        for section in self.data:
            for record in self.data[section]:
                meas = {
                    "measurement": f"{self.tag}_{section}_{record[0]}",
                    "tags": {
                        # "description": tag['description'],
                        "eu": record[2],
                        "location": self.locate,
                        "type": section
                    },
                    "time": self.dt,
                    "fields": {
                        "value": record[1]
                    }
                }
                self.influxdb_body.append(meas)


def main():
    # Database connection
    logger.info(f"Connecting to InfluxDB {_IP_INFLUXDB}")
    idb = InfluxDBHelper(host=_IP_INFLUXDB, db_name='COMPRESSORS')
    for comp in _COMPRESSORS:
        comp_data = Compressor(*comp)
        if len(comp_data.influxdb_body) > 0:
            logger.info(f"Data from {comp} OK.")
            idb.write_points(comp_data.influxdb_body)
            logger.debug(comp_data.influxdb_body)
        else:
            logger.info(f"Data from {comp} NOT RECEIVED.")


if __name__ == '__main__':
    main()

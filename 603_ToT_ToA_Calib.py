import packetlib
import socket
import numpy as np
import time
import json
import os
import logging
import colorlog
from icmplib import ping
from tqdm import tqdm

import matplotlib.pyplot as plt


# * --- Set up script information -------------------------------------
script_id_str       = '603_ToT_Calib'
script_version_str  = '0.1'

# * --- Test function -------------------------------------------------

def measure_v0v1v2(_socket_udp, _ip, _port, _fpga_address, _reg_runLR, _reg_offLR, _event_num, _fragment_life, _logger):
    for _asic in range(2):
        if not packetlib.send_check_i2c_wrapper(_socket_udp, _ip, _port, asic_num=_asic, fpga_addr = _fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=_reg_runLR, retry=5, verbose=False):
            _logger.warning(f"Failed to turn on LR for ASIC {_asic}")

    packetlib.clean_socket(_socket_udp)

    if not packetlib.send_daq_gen_start_stop(_socket_udp, _ip, _port, asic_num=0, fpga_addr = _fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
        _logger.warning("Failed to start the generator")

    extracted_payloads_pool = []
    event_fragment_pool     = []
    fragment_life_dict      = {}

    current_half_packet_num = 0
    current_event_num = 0

    all_chn_value_0_array = np.zeros((_event_num, 152))
    all_chn_value_1_array = np.zeros((_event_num, 152))
    all_chn_value_2_array = np.zeros((_event_num, 152))
    hamming_code_array    = np.zeros((_event_num, 12))

    while True:
        try:
            data_packet, rec_addr    = _socket_udp.recvfrom(8192)
            # _logger.debug("Packet received")
            extracted_payloads_pool += packetlib.extract_raw_payloads(data_packet)
            while len(extracted_payloads_pool) >= 5:
                candidate_packet_lines = extracted_payloads_pool[:5]
                is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
                if is_packet_good:
                    event_fragment_pool.append(event_fragment)
                    current_half_packet_num += 1
                    extracted_payloads_pool = extracted_payloads_pool[5:]
                else:
                    _logger.warning("Warning: Event fragment is not good")
                    extracted_payloads_pool = extracted_payloads_pool[1:]
            indices_to_delete = set()
            if len(event_fragment_pool) >= 4:
                event_fragment_pool = sorted(event_fragment_pool, key=lambda x: x[0][3:7])
            i = 0
            while i <= len(event_fragment_pool) - 4:
                timestamp0 = event_fragment_pool[i][0][4] << 24 | event_fragment_pool[i][0][5] << 16 | event_fragment_pool[i][0][6] << 8 | event_fragment_pool[i][0][7]
                timestamp1 = event_fragment_pool[i+1][0][4] << 24 | event_fragment_pool[i+1][0][5] << 16 | event_fragment_pool[i+1][0][6] << 8 | event_fragment_pool[i+1][0][7]
                timestamp2 = event_fragment_pool[i+2][0][4] << 24 | event_fragment_pool[i+2][0][5] << 16 | event_fragment_pool[i+2][0][6] << 8 | event_fragment_pool[i+2][0][7]
                timestamp3 = event_fragment_pool[i+3][0][4] << 24 | event_fragment_pool[i+3][0][5] << 16 | event_fragment_pool[i+3][0][6] << 8 | event_fragment_pool[i+3][0][7]
                if timestamp0 == timestamp1 and timestamp0 == timestamp2 and timestamp0 == timestamp3:
                    id_str = f"{timestamp0:08X}"
                    for _half in range(4):
                        extracted_data = packetlib.assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
                        extracted_values = packetlib.extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
                        uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
                        for j in range(len(extracted_values["_extracted_values"])):
                            all_chn_value_0_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
                            all_chn_value_1_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
                            all_chn_value_2_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
                        hamming_code_array[current_event_num][_half*3+0] =  packetlib.DaqH_get_H1(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+1] =  packetlib.DaqH_get_H2(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+2] =  packetlib.DaqH_get_H3(extracted_values["_DaqH"])
                    indices_to_delete.update([i, i+1, i+2, i+3])
                    current_event_num += 1
                    i += 4
                else:
                    if timestamp0 in fragment_life_dict:
                        if fragment_life_dict[timestamp0] >= _fragment_life - 1:
                            indices_to_delete.update([i])
                            del fragment_life_dict[timestamp0]
                        else:
                            fragment_life_dict[timestamp0] += 1
                    else:
                        fragment_life_dict[timestamp0] = 1
                    i += 1
            for index in sorted(indices_to_delete, reverse=True):
                del event_fragment_pool[index]
            if current_event_num == _event_num:
                break;      
        except Exception as e:
            _logger.warning("Exception in receiving data")
            _logger.warning(e)
            _logger.warning('Packet received: ' + str(current_half_packet_num))
            _logger.warning('left fragments:' + str(len(event_fragment_pool)))
            _logger.warning("current event num:" + str(current_event_num))
            measurement_good_flag = False
            break

    if not np.all(hamming_code_array == 0):
        _logger.warning("Hamming code error detected!")
        measurement_good_flag = False
    if not packetlib.send_daq_gen_start_stop(_socket_udp, _ip, _port, asic_num=0, fpga_addr = _fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
        _logger.warning("Failed to stop the generator")
    for _asic in range(2):
        if not packetlib.send_check_i2c_wrapper(_socket_udp, _ip, _port, asic_num=_asic, fpga_addr = _fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=_reg_offLR, retry=5, verbose=False):
            _logger.warning(f"Failed to turn off LR for ASIC {_asic}")
    _val0_mean_list = []
    _val0_err_list  = []
    _val1_mean_list = []
    _val1_err_list  = []
    _val2_mean_list = []
    _val2_err_list  = []

    for _chn in range(152):
        _candidate_v0_values = []
        _candidate_v1_values = []
        _candidate_v2_values = []
        for _event in range(_event_num):
            if np.all(hamming_code_array[_event] == 0):
                _candidate_v0_values.append(all_chn_value_0_array[_event][_chn])
                _candidate_v1_values.append(all_chn_value_1_array[_event][_chn])
                _candidate_v2_values.append(all_chn_value_2_array[_event][_chn])
        if len(_candidate_v0_values) > 0:
            _val0_mean_list.append(np.max(_candidate_v0_values))
            _val0_err_list.append(np.std(_candidate_v0_values))
        else:
            _logger.warning(f"Channel {_chn} has no valid v0")
            _val0_mean_list.append(0)
            _val0_err_list.append(0)
        if len(_candidate_v1_values) > 0:
            _val1_mean_list.append(np.max(_candidate_v1_values))
            _val1_err_list.append(np.std(_candidate_v1_values))
        else:
            _logger.warning(f"Channel {_chn} has no valid v1")
            _val1_mean_list.append(0)
            _val1_err_list.append(0)
        if len(_candidate_v2_values) > 0:
            _val2_mean_list.append(np.max(_candidate_v2_values))
            _val2_err_list.append(np.std(_candidate_v2_values))
        else:
            _logger.warning(f"Channel {_chn} has no valid v2")
            _val2_mean_list.append(0)
            _val2_err_list.append(0)
    return _val0_mean_list, _val0_err_list, _val1_mean_list, _val1_err_list, _val2_mean_list, _val2_err_list

# * --- Set up logging ------------------------------------------------
class TqdmColorLoggingHandler(colorlog.StreamHandler):
    def __init__(self):
        super().__init__()
    
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)

# Configure the custom logging handler with colored output
handler = TqdmColorLoggingHandler()
formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',  # Customizes the date format to show only time
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
)
handler.setFormatter(formatter)

logger = logging.getLogger('example_logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# * --- Set up output folder -------------------------------------------
output_dump_path = 'dump'   # dump is for temporary files like config
output_data_path = 'data'   # data is for very-likely-to-be-used files

output_folder_name      = f'{script_id_str}_data_{time.strftime("%Y%m%d_%H%M%S")}'
output_config_json_name = f'{script_id_str}_config_{time.strftime("%Y%m%d_%H%M%S")}.json'
output_data_folder_name = f'{script_id_str}_data_{time.strftime("%Y%m%d_%H%M%S")}'
output_config_json = {}
output_pedecalib_json = {}

output_data_path = os.path.join(output_data_path, output_folder_name)

output_dump_folder = os.path.join(output_dump_path, output_folder_name)
output_config_path = os.path.join(output_dump_path, output_config_json_name)

common_settings_json_path = "common_settings.json"
is_common_settings_exist = False
try :
    with open(common_settings_json_path, 'r') as json_file:
        common_settings = json.load(json_file)
        is_common_settings_exist = True
except FileNotFoundError:
    logger.info(f"Common settings file not found: {common_settings_json_path}")

if not os.path.exists(output_data_path):
    os.makedirs(output_data_path)
if not os.path.exists(output_dump_path):
    os.makedirs(output_dump_path)
if not os.path.exists(output_dump_folder):
    os.makedirs(output_dump_folder)

# * --- Set up socket -------------------------------------------------
h2gcroc_ip      = "10.1.2.208"
pc_ip           = "10.1.2.207"
h2gcroc_port    = 11000
pc_port         = 11000
timeout         = 3 # seconds

if is_common_settings_exist:
    try:
        udp_settings = common_settings['udp']
        h2gcroc_ip = udp_settings['h2gcroc_ip']
        pc_ip = udp_settings['pc_ip']
        h2gcroc_port = udp_settings['h2gcroc_port']
        pc_port = udp_settings['pc_port']
    except KeyError:
        logger.warning("Common settings file does not contain UDP settings")

logger.info(f"UDP settings: H2GCROC IP: {h2gcroc_ip}, PC IP: {pc_ip}, H2GCROC Port: {h2gcroc_port}, PC Port: {pc_port}")

ping_result = ping(pc_ip, count=1)
if ping_result.is_alive:
    logger.info(f"PC IP {pc_ip} is reachable")
else:
    logger.critical(f"PC IP {pc_ip} is not reachable")
    logger.critical("Please check the network settings")
    exit()

output_config_json['udp'] = {
    'h2gcroc_ip': h2gcroc_ip,
    'pc_ip': pc_ip,
    'h2gcroc_port': h2gcroc_port,
    'pc_port': pc_port,
    'timeout': timeout
}

socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_udp.bind((pc_ip, pc_port))
socket_udp.settimeout(timeout)

# * I2C register settings
# * ---------------------------------------------------------------------------
i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

top_reg_runLR = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
top_reg_offLR = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]

default_global_analog   = reg_settings.get_default_reg_content('registers_global_analog')
default_global_analog[8]  = 0xA0
default_global_analog[9]  = 0xCA
default_global_analog[10] = 0x42
default_global_analog[14] = 0x6F

default_channel_wise    = reg_settings.get_default_reg_content('registers_channel_wise')
# default_channel_wise[4]  = 0x02 # low range
default_channel_wise[14] = 0xC0

default_reference_voltage = reg_settings.get_default_reg_content('registers_reference_voltage')
default_reference_voltage[10] = 0x40 # choice_cinj

default_digital_half = reg_settings.get_default_reg_content('registers_digital_half')
default_digital_half[4]  = 0xC0 # force calibration mode
default_digital_half[25] = 0x02

output_config_json["i2c"] = {}
output_config_json["i2c"]["top_reg_runLR"] = top_reg_runLR
output_config_json["i2c"]["top_reg_offLR"] = top_reg_offLR

# * Find the newest pedestal calibration file
# * ---------------------------------------------------------------------------
pedestal_calib_file_prefix = "pede_calib_config"
pedestal_calib_folder = "dump"
pedestal_calib_files = [f for f in os.listdir(pedestal_calib_folder) if f.startswith(pedestal_calib_file_prefix)]
pedestal_calib_files.sort(reverse=True)

newest_pedestal_calib_file_found = False
if len(pedestal_calib_files) > 0:
    for _file in pedestal_calib_files:
        logger.info(f"Found pedestal calibration file: {_file}")
        newest_pedestal_calib_file = _file
        with open(os.path.join(pedestal_calib_folder, newest_pedestal_calib_file), 'r') as json_file:
            pedestal_calib = json.load(json_file)
            if pedestal_calib['udp']['h2gcroc_ip'] == h2gcroc_ip:
                newest_pedestal_calib_file_found = True
                break

if not newest_pedestal_calib_file_found:
    logger.critical("No pedestal calibration file found for the current H2GCROC IP")
    exit()

logger.info(f"Found newest pedestal calibration file: {newest_pedestal_calib_file}")

trim_dac_values     = []
inputdac_values     = []
noinv_vref_list     = []
inv_vref_list       = []
dead_channels       = []
not_used_channels   = []

pedestal_value = 100

with open(os.path.join(pedestal_calib_folder, newest_pedestal_calib_file), 'r') as json_file:
    pedestal_calib      = json.load(json_file)
    noinv_vref_list     = pedestal_calib["noinv_vref_list"]
    inv_vref_list       = pedestal_calib["inv_vref_list"]
    trim_dac_values     = pedestal_calib["chn_trim_settings"]
    inputdac_values     = pedestal_calib["chn_inputdac_settings"]
    dead_channels       = pedestal_calib["dead_channels"]
    not_used_channels   = pedestal_calib["channel_not_used"]
    pedestal_value      = pedestal_calib["running_parameters"]["target_pedestal"]

if len(noinv_vref_list) == 0 or len(inv_vref_list) == 0 or len(trim_dac_values) == 0:
    logger.critical("Pedestal calibration file format is incorrect")
    exit()

logger.debug(f"Dead channels: {dead_channels}")
logger.debug(f"Not used channels: {not_used_channels}")

# * --- Set running parameters ------------------------------------------------
total_asic          = 2
fpga_address        = int(h2gcroc_ip.split('.')[-1]) - 208

machine_gun_val             = 0
gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011
gen_pre_inverval_value      = 18
gen_nr_cycle                = 1
gen_interval_value          = 100

phase_setting = 13

_12b_dac      = 500

# ! The best for Board A
toa_global_threshold = [123, 133, 134, 138]
# ! The best for Board B
# toa_global_threshold = [135, 135, 135, 138]
# ! The best for Board B 2
# toa_global_threshold = [135, 135, 135, 135]
# ! The best for Board A
tot_global_threshold = [450, 480, 475, 475]
# ! The best for Board B
# tot_global_threshold = [483, 470, 600, 485]
# ! The best for Board B 2
# tot_global_threshold = [480, 480, 470, 480]

# chn_tot_threshold_trim = [0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 0, 20, 20, 20, 20, 0, 20, 5, 20, 20, 20, 5, 20, 5, 10, 10, 20, 0, 0, 20, 20, 5, 10, 20, 20, 0, 20, 20, 20, 20, 20, 20, 0, 20, 20, 10, 20, 0, 20, 20, 20, 20, 20, 20, 20, 20, 0, 20, 20, 0, 20, 0, 20, 20, 20, 0, 0, 20, 20, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 20, 0, 20, 20, 20, 0, 20, 0, 20, 20, 20, 20, 20, 0, 20, 20, 20, 20, 20, 20, 20, 0, 20, 20, 20, 0]

# chn_tot_threshold_trim = [0, 40, 30, 40, 40, 40, 40, 40, 15, 40, 40, 15, 15, 15, 40, 15, 40, 40, 40, 0, 20, 25, 21, 20, 25, 20, 30, 10, 30, 25, 30, 15, 25, 10, 20, 20, 40, 0, 0, 40, 30, 10, 20, 40, 25, 0, 40, 40, 40, 40, 40, 30, 0, 30, 40, 20, 40, 0, 30, 40, 40, 40, 40, 40, 40, 40, 0, 40, 40, 0, 40, 0, 30, 40, 40, 0, 0, 40, 40, 0, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 30, 30, 0, 40, 40, 40, 40, 40, 21, 40, 21, 40, 40, 40, 40, 40, 40, 20, 40, 40, 0, 0, 40, 30, 30, 30, 40, 30, 30, 30, 40, 30, 20, 40, 0, 40, 30, 30, 20, 25, 0, 30, 40, 40, 40, 40, 0, 40, 19, 40, 40, 40, 40, 40, 20, 40, 30, 30, 0]

# chn_tot_threshold_trim = [0, 60, 50, 60, 35, 30, 35, 30, 35, 39, 35, 5, 10, 10, 35, 5, 60, 60, 60, 0, 0, 30, 22, 20, 35, 0, 40, 15, 35, 35, 40, 25, 30, 15, 30, 30, 60, 0, 0, 60, 40, 15, 30, 60, 26, 0, 60, 45, 60, 60, 50, 50, 0, 40, 60, 30, 41, 0, 35, 50, 60, 60, 60, 60, 30, 60, 0, 60, 60, 0, 60, 0, 40, 50, 60, 0, 0, 60, 60, 0, 60, 60, 60, 60, 60, 60, 60, 60, 30, 60, 60, 60, 60, 40, 40, 0, 60, 60, 35, 40, 41, 22, 40, 21, 41, 40, 60, 41, 60, 60, 20, 60, 60, 0, 0, 60, 40, 40, 50, 60, 40, 40, 40, 60, 40, 40, 30, 0, 30, 40, 40, 30, 30, 0, 40, 50, 30, 30, 30, 0, 30, 14, 35, 39, 60, 35, 39, 40, 60, 40, 40, 0]

# ! The best for Board A
chn_tot_threshold_trim = [0, 63, 63, 63, 30, 20, 25, 20, 30, 39, 30, 25, 5, 5, 55, 25, 40, 63, 63, 0, 0, 35, 23, 21, 40, 0, 50, 20, 40, 45, 50, 35, 35, 20, 40, 40, 63, 0, 0, 63, 50, 20, 40, 50, 31, 0, 63, 50, 50, 63, 60, 40, 0, 50, 63, 40, 42, 0, 40, 60, 50, 55, 50, 55, 20, 59, 0, 60, 61, 0, 60, 0, 60, 63, 63, 0, 0, 63, 60, 0, 63, 63, 63, 50, 55, 60, 55, 50, 50, 63, 55, 63, 63, 50, 50, 0, 55, 60, 34, 40, 42, 22, 40, 21, 46, 40, 60, 46, 63, 63, 21, 63, 63, 0, 0, 63, 50, 50, 40, 50, 50, 50, 50, 50, 20, 60, 50, 0, 40, 50, 50, 40, 35, 0, 50, 60, 50, 40, 20, 0, 25, 9, 35, 38, 59, 55, 39, 60, 63, 50, 50, 0]

# ! Testing for Board B
# chn_tot_threshold_trim = [0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 0, 0, 0, 10, 0, 10, 0, 0, 0, 0, 10, 20, 10, 20, 0, 10, 10, 10, 0, 0, 20, 20, 0, 0, 0, 20, 0, 20, 0, 20, 0, 0, 20, 20, 0, 20, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 20, 20, 20, 20, 20, 20, 0, 20, 20, 10, 20, 20, 20, 20, 20, 20, 20, 0, 20, 20, 20, 0, 20, 20, 20, 20, 20, 20, 20, 0, 20, 10, 20, 20, 20, 0]

# chn_tot_threshold_trim = [0, 30, 40, 40, 40, 30, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 30, 30, 0, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 20, 40, 40, 40, 40, 0, 0, 20, 0, 20, 20, 20, 10, 10, 10, 10, 0, 40, 15, 30, 20, 20, 20, 20, 0, 0, 0, 0, 0, 20, 20, 40, 20, 40, 20, 40, 0, 20, 40, 40, 20, 21, 40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 40, 30, 40, 30, 30, 40, 40, 0, 40, 40, 20, 40, 40, 40, 40, 40, 40, 30, 0, 40, 40, 40, 0, 40, 40, 40, 40, 40, 40, 40, 0, 30, 20, 30, 40, 40, 0]

# chn_tot_threshold_trim = [0, 40, 50, 60, 60, 40, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 40, 40, 0, 40, 40, 60, 60, 60, 60, 41, 60, 60, 60, 41, 40, 20, 41, 60, 45, 60, 0, 0, 0, 0, 30, 30, 0, 0, 15, 30, 20, 10, 60, 20, 50, 40, 30, 30, 30, 1, 0, 0, 20, 20, 0, 40, 60, 0, 60, 40, 60, 0, 40, 60, 60, 30, 22, 60, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 60, 40, 60, 40, 35, 60, 60, 0, 45, 60, 30, 60, 60, 60, 60, 60, 60, 40, 0, 60, 50, 60, 0, 60, 35, 60, 60, 39, 60, 60, 0, 40, 30, 40, 50, 20, 0]

# chn_tot_threshold_trim = [0, 50, 60, 63, 55, 50, 63, 50, 50, 63, 50, 63, 59, 55, 63, 55, 63, 60, 50, 0, 40, 41, 60, 61, 61, 60, 46, 63, 63, 63, 42, 40, 20, 41, 61, 50, 63, 0, 0, 0, 0, 40, 40, 5, 0, 25, 40, 30, 0, 50, 25, 60, 20, 40, 40, 40, 6, 0, 0, 25, 0, 20, 60, 50, 0, 40, 60, 40, 20, 60, 63, 55, 40, 27, 63, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 63, 50, 63, 50, 45, 63, 63, 0, 50, 63, 40, 63, 63, 50, 63, 63, 63, 50, 0, 63, 60, 50, 0, 50, 55, 55, 55, 38, 60, 63, 0, 50, 40, 50, 60, 40, 0]

# ! Best for Board B
# chn_tot_threshold_trim = [0, 63, 63, 63, 50, 40, 58, 40, 50, 63, 50, 63, 54, 50, 53, 35, 53, 63, 63, 0, 20, 46, 60, 56, 63, 40, 51, 63, 63, 63, 52, 50, 25, 46, 63, 60, 63, 0, 0, 20, 20, 20, 50, 25, 20, 25, 60, 35, 20, 63, 45, 50, 0, 50, 60, 50, 26, 0, 20, 35, 20, 40, 50, 63, 20, 60, 60, 60, 40, 60, 63, 63, 60, 47, 63, 0, 0, 0, 0, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 10, 20, 20, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 5, 20, 20, 0, 0, 63, 63, 53, 40, 63, 63, 63, 20, 60, 53, 50, 53, 43, 50, 63, 63, 63, 55, 0, 63, 63, 60, 20, 50, 35, 45, 54, 38, 61, 63, 20, 51, 60, 50, 60, 40, 0]

# Testing Board B 2
# chn_tot_threshold_trim = [0, 20, 20, 20, 20, 20, 10, 20, 20, 5, 20, 10, 10, 10, 10, 20, 20, 20, 0, 0, 20, 20, 20, 20, 20, 20, 20, 20, 10, 20, 20, 10, 20, 20, 20, 20, 20, 0, 0, 0, 20, 0, 0, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 10, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 10, 20, 20, 20, 20, 20, 0, 0, 20, 20, 0, 20, 20, 0, 0, 20, 20, 20, 20, 20, 20, 20, 0, 20, 0, 0, 0, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0, 0, 0, 0, 20, 10, 20, 20, 20, 20, 10, 20, 0, 20, 20, 20, 20, 0, 20, 20, 20, 0, 10, 20, 20, 20, 20, 20, 0, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 0]

# ! The best for Board B 2
# chn_tot_threshold_trim = [0, 40, 40, 20, 40, 30, 20, 30, 25, 6, 20, 10, 20, 20, 20, 25, 40, 40, 0, 0, 30, 40, 40, 30, 40, 40, 40, 40, 20, 40, 40, 30, 40, 40, 40, 40, 40, 0, 0, 0, 40, 0, 0, 0, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 20, 0, 40, 40, 40, 40, 40, 40, 40, 40, 20, 40, 21, 20, 40, 40, 40, 40, 40, 0, 0, 40, 25, 20, 40, 40, 20, 20, 40, 40, 40, 40, 40, 40, 40, 20, 40, 0, 20, 0, 20, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 20, 0, 0, 0, 40, 30, 40, 40, 30, 40, 20, 40, 0, 40, 30, 40, 30, 0, 30, 40, 30, 0, 20, 25, 40, 40, 40, 40, 20, 40, 40, 19, 40, 40, 40, 10, 40, 40, 30, 0]

while len(chn_tot_threshold_trim) < 152:
    chn_tot_threshold_trim.append(0)

# chn_toa_threshold_trim = [0, 10, 10, 20, 10, 10, 10, 10, 10, 20, 5, 10, 5, 5, 10, 10, 5, 10, 10, 0, 0, 10, 20, 10, 20, 0, 20, 5, 5, 20, 20, 5, 10, 5, 10, 10, 10, 0, 0, 10, 10, 0, 5, 10, 10, 0, 10, 10, 10, 10, 10, 0, 5, 20, 5, 10, 0, 10, 10, 5, 5, 10, 5, 5, 10, 20, 5, 20, 5, 10, 20, 10, 10, 10, 0, 0, 10, 10, 0, 10, 20, 20, 5, 10, 10, 10, 5, 10, 5, 10, 5, 10, 0, 0, 5, 10, 10, 10, 0, 20, 10, 20, 5, 10, 10, 20, 20, 5, 20, 10, 0, 0, 10, 10, 10, 20, 20, 20, 10, 10, 10, 10, 0, 0, 5, 0, 5, 5, 5, 10, 0, 10, 5, 20, 20, 10, 5, 10, 20, 20, 20, 0]

# chn_toa_threshold_trim = [0, 20, 20, 30, 11, 20, 20, 15, 15, 30, 10, 15, 5, 10, 15, 20, 15, 10, 20, 0, 0, 15, 25, 11, 25, 0, 40, 10, 15, 40, 25, 15, 15, 15, 20, 10, 20, 0, 0, 10, 10, 0, 6, 11, 20, 0, 20, 15, 20, 15, 11, 1, 5, 20, 15, 15, 10, 10, 10, 15, 5, 15, 15, 10, 10, 25, 15, 20, 15, 20, 25, 20, 11, 20, 20, 0, 10, 20, 10, 10, 20, 30, 25, 10, 20, 10, 6, 10, 10, 20, 10, 11, 10, 10, 5, 10, 15, 20, 0, 25, 11, 20, 15, 20, 20, 20, 25, 10, 30, 20, 5, 10, 20, 10, 10, 20, 20, 20, 20, 30, 20, 10, 10, 10, 15, 1, 15, 5, 10, 10, 0, 10, 5, 20, 20, 15, 6, 10, 21, 20, 25, 5, 5, 20, 10, 10, 5, 10, 20, 20, 20, 0]

# chn_toa_threshold_trim = [0, 25, 20, 35, 16, 21, 21, 20, 20, 31, 9, 20, 5, 10, 20, 25, 15, 10, 20, 0, 0, 25, 30, 16, 30, 5, 45, 15, 20, 45, 30, 20, 25, 15, 20, 10, 20, 0, 0, 10, 20, 0, 7, 12, 20, 0, 0, 25, 25, 20, 16, 2, 0, 19, 25, 16, 10, 10, 10, 15, 4, 20, 20, 9, 10, 25, 25, 19, 25, 20, 30, 30, 11, 20, 20, 0, 10, 21, 20, 10, 20, 31, 35, 9, 21, 15, 7, 9, 15, 21, 9, 11, 10, 10, 5, 10, 16, 21, 5, 30, 16, 10, 25, 25, 30, 19, 30, 15, 40, 25, 15, 30, 20, 10, 10, 20, 21, 21, 30, 31, 25, 5, 20, 15, 16, 2, 16, 0, 11, 5, 0, 9, 5, 20, 20, 15, 11, 5, 22, 0, 30, 10, 10, 21, 20, 15, 10, 15, 40, 25, 30, 0]

# chn_toa_threshold_trim = [0, 25, 20, 40, 17, 22, 22, 19, 21, 32, 8, 20, 4, 10, 25, 30, 15, 10, 20, 0, 10, 25, 35, 21, 35, 0, 45, 20, 20, 45, 35, 20, 24, 15, 20, 10, 20, 0, 0, 9, 20, 0, 7, 13, 25, 0, 10, 25, 30, 25, 17, 7, 0, 18, 30, 21, 10, 10, 10, 16, 0, 19, 25, 8, 10, 24, 35, 19, 30, 20, 35, 35, 11, 20, 21, 0, 10, 22, 21, 10, 21, 36, 45, 8, 22, 16, 8, 8, 15, 22, 10, 12, 10, 9, 5, 10, 21, 22, 0, 31, 21, 10, 26, 30, 35, 18, 31, 16, 45, 30, 25, 30, 20, 10, 10, 20, 21, 22, 31, 32, 30, 0, 20, 16, 17, 3, 17, 0, 12, 5, 0, 4, 5, 20, 20, 15, 12, 6, 23, 0, 29, 15, 15, 26, 30, 20, 11, 16, 50, 35, 40, 0]

# chn_toa_threshold_trim = [0, 30, 20, 40, 22, 27, 27, 24, 20, 33, 7, 19, 4, 10, 24, 29, 15, 10, 20, 0, 0, 24, 34, 26, 35, 10, 44, 20, 20, 44, 40, 20, 29, 15, 20, 10, 20, 0, 0, 9, 25, 0, 8, 14, 25, 0, 20, 25, 25, 30, 18, 8, 0, 17, 31, 20, 10, 10, 10, 16, 1, 18, 26, 13, 10, 23, 40, 19, 35, 20, 35, 40, 11, 20, 21, 0, 10, 27, 22, 10, 16, 37, 45, 7, 22, 16, 8, 3, 15, 32, 11, 12, 10, 8, 5, 10, 20, 27, 1, 32, 20, 9, 31, 35, 40, 18, 30, 21, 46, 35, 24, 35, 20, 10, 10, 19, 22, 23, 31, 33, 31, 1, 21, 17, 18, 4, 22, 0, 13, 5, 0, 3, 5, 20, 20, 15, 11, 1, 22, 0, 28, 16, 20, 27, 35, 25, 16, 17, 50, 35, 40, 0]

# ! The best for Board A
# chn_toa_threshold_trim = [0, 30, 20, 40, 27, 32, 32, 24, 20, 38, 7, 19, 3, 10, 24, 28, 15, 10, 20, 0, 0, 24, 34, 25, 40, 15, 45, 20, 20, 44, 40, 20, 29, 15, 20, 10, 25, 0, 0, 9, 30, 0, 8, 19, 25, 0, 20, 25, 26, 25, 23, 8, 20, 16, 36, 25, 15, 10, 20, 16, 6, 17, 26, 13, 10, 22, 40, 18, 40, 20, 34, 39, 11, 20, 21, 0, 10, 27, 22, 10, 11, 42, 46, 7, 23, 11, 9, 2, 15, 31, 10, 13, 15, 13, 5, 10, 15, 28, 2, 27, 25, 4, 32, 34, 40, 17, 30, 16, 51, 36, 24, 34, 21, 10, 10, 14, 23, 28, 36, 34, 32, 0, 22, 22, 23, 5, 23, 0, 12, 0, 0, 3, 4, 20, 20, 15, 11, 6, 27, 0, 27, 15, 19, 28, 36, 30, 26, 22, 55, 35, 40, 0]

# chn_toa_threshold_trim = [0, 29, 20, 40, 26, 31, 33, 24, 25, 43, 7, 19, 3, 9, 24, 28, 0, 10, 20, 0, 0, 4, 33, 25, 40, 0, 45, 20, 20, 43, 39, 20, 28, 15, 20, 10, 5, 0, 0, 10, 25, 0, 13, 20, 25, 0, 21, 25, 31, 30, 22, 7, 0, 15, 41, 20, 15, 10, 20, 16, 6, 16, 25, 13, 5, 21, 39, 18, 40, 19, 33, 39, 21, 20, 31, 0, 10, 27, 22, 10, 12, 37, 47, 7, 24, 12, 10, 2, 14, 36, 5, 14, 14, 8, 4, 10, 20, 27, 1, 27, 20, 3, 37, 33, 40, 12, 29, 21, 52, 41, 23, 33, 26, 10, 10, 9, 24, 23, 37, 35, 33, 0, 23, 21, 24, 6, 24, 0, 11, 1, 0, 3, 4, 20, 19, 14, 11, 1, 22, 0, 26, 20, 14, 29, 37, 30, 25, 23, 54, 35, 40, 0] 

# chn_toa_threshold_trim = [0, 28, 20, 40, 25, 36, 28, 24, 25, 43, 7, 19, 3, 9, 24, 28, 10, 10, 20, 0, 10, 14, 32, 25, 40, 0, 44, 20, 19, 43, 39, 19, 28, 15, 20, 10, 10, 0, 0, 11, 25, 0, 12, 21, 25, 0, 21, 25, 30, 30, 21, 6, 0, 10, 36, 20, 15, 10, 20, 16, 5, 21, 24, 13, 10, 26, 39, 18, 40, 19, 33, 38, 21, 20, 31, 0, 10, 27, 32, 10, 13, 32, 48, 7, 25, 17, 11, 0, 13, 31, 10, 15, 13, 13, 4, 10, 19, 28, 6, 22, 25, 2, 32, 38, 39, 17, 34, 20, 57, 36, 23, 32, 21, 10, 10, 10, 19, 24, 32, 45, 43, 0, 24, 20, 29, 7, 24, 0, 11, 2, 0, 2, 4, 20, 19, 13, 6, 6, 17, 0, 31, 19, 19, 34, 38, 30, 24, 28, 54, 35, 45, 0]

# chn_toa_threshold_trim =  [0, 33, 19, 30, 30, 26, 33, 19, 15, 43, 0, 14, 0, 0, 4, 29, 10, 5, 25, 0, 15, 19, 37, 15, 20, 0, 24, 0, 14, 23, 34, 0, 28, 16, 21, 11, 11, 0, 0, 31, 26, 0, 12, 21, 45, 0, 11, 20, 30, 50, 41, 0, 0, 0, 41, 10, 35, 10, 40, 11, 5, 22, 25, 14, 5, 27, 40, 8, 45, 20, 28, 39, 11, 40, 21, 0, 10, 17, 32, 20, 12, 42, 47, 0, 15, 17, 12, 10, 13, 31, 20, 15, 13, 13, 9, 10, 14, 28, 7, 23, 24, 2, 37, 33, 40, 17, 35, 20, 57, 16, 24, 22, 16, 10, 10, 5, 19, 19, 31, 45, 43, 0, 19, 21, 29, 7, 19, 0, 11, 0, 0, 0, 0, 20, 14, 14, 6, 1, 17, 0, 31, 19, 20, 39, 38, 20, 19, 23, 54, 25, 35, 0]

chn_toa_threshold_trim = [0, 28, 19, 25, 20, 21, 34, 19, 14, 43, 0, 14, 0, 0, 9, 29, 11, 4, 30, 0, 16, 20, 37, 16, 0, 0, 4, 0, 0, 3, 14, 0, 29, 17, 22, 1, 21, 0, 0, 51, 27, 0, 12, 11, 40, 0, 16, 25, 20, 50, 36, 5, 0, 10, 42, 11, 40, 10, 20, 31, 5, 22, 25, 4, 4, 17, 41, 3, 50, 21, 27, 44, 11, 20, 41, 0, 10, 17, 52, 19, 12, 41, 47, 5, 15, 18, 7, 5, 3, 30, 40, 15, 18, 18, 4, 10, 9, 18, 7, 24, 24, 7, 36, 33, 41, 22, 30, 20, 58, 0, 24, 27, 16, 10, 10, 0, 19, 20, 32, 45, 43, 0, 19, 11, 24, 7, 20, 0, 11, 1, 0, 1, 1, 20, 19, 15, 7, 1, 17, 0, 31, 20, 21, 39, 37, 19, 14, 18, 54, 20, 35, 0]


# ! Testing for Board B
# chn_toa_threshold_trim = [0, 0, 20, 20, 10, 5, 20, 1, 5, 10, 5, 5, 5, 10, 10, 5, 10, 10, 10, 0, 10, 10, 5, 1, 10, 10, 10, 10, 10, 10, 10, 5, 10, 5, 10, 5, 5, 0, 0, 0, 10, 10, 10, 0, 10, 0, 5, 10, 10, 10, 5, 10, 20, 10, 10, 10, 20, 0, 10, 5, 10, 10, 10, 5, 5, 10, 20, 20, 10, 10, 20, 20, 20, 20, 20, 0, 0, 10, 20, 10, 10, 10, 10, 0, 5, 5, 5, 5, 0, 10, 10, 10, 20, 20, 10, 0, 10, 10, 10, 10, 10, 10, 10, 10, 10, 5, 10, 0, 20, 20, 20, 10, 10, 0, 0, 10, 1, 10, 10, 5, 5, 10, 0, 10, 5, 10, 10, 5, 5, 10, 5, 10, 10, 0, 10, 20, 5, 20, 10, 1, 5, 10, 5, 20, 20, 0, 20, 0, 5, 10, 20, 0]

# chn_toa_threshold_trim = [0, 0, 30, 20, 20, 10, 30, 2, 10, 20, 10, 10, 10, 15, 11, 10, 10, 10, 10, 0, 15, 11, 10, 6, 20, 15, 20, 11, 20, 15, 15, 10, 15, 10, 15, 15, 10, 0, 0, 20, 0, 0, 0, 10, 20, 5, 10, 20, 0, 15, 5, 20, 30, 15, 20, 20, 25, 0, 20, 10, 20, 15, 15, 4, 25, 15, 30, 30, 15, 30, 25, 40, 30, 30, 40, 0, 0, 15, 25, 15, 20, 20, 11, 1, 10, 10, 6, 10, 0, 20, 20, 10, 30, 25, 15, 0, 15, 15, 20, 15, 20, 15, 15, 20, 20, 10, 15, 0, 25, 30, 25, 15, 11, 0, 0, 15, 6, 20, 11, 10, 10, 15, 0, 15, 6, 15, 20, 10, 10, 20, 6, 15, 15, 0, 15, 25, 10, 0, 15, 6, 10, 15, 10, 30, 30, 0, 30, 0, 5, 20, 25, 0]

# chn_toa_threshold_trim = [0, 0, 35, 30, 21, 15, 30, 3, 15, 30, 5, 15, 15, 20, 16, 15, 10, 10, 10, 0, 20, 12, 15, 7, 25, 20, 25, 16, 21, 20, 20, 15, 25, 15, 20, 14, 15, 0, 0, 30, 20, 10, 10, 15, 25, 10, 15, 20, 10, 20, 5, 30, 40, 20, 20, 40, 35, 0, 25, 0, 0, 20, 20, 0, 24, 20, 40, 40, 20, 35, 25, 50, 40, 30, 20, 0, 0, 20, 30, 20, 25, 21, 16, 6, 15, 15, 7, 11, 0, 21, 25, 15, 35, 25, 20, 0, 20, 20, 25, 20, 21, 20, 20, 25, 25, 15, 20, 0, 25, 35, 30, 20, 16, 0, 0, 20, 11, 25, 16, 15, 10, 25, 0, 20, 11, 16, 25, 15, 5, 20, 0, 20, 20, 0, 20, 30, 15, 0, 20, 11, 20, 20, 20, 35, 30, 0, 30, 0, 5, 20, 30, 0]

# ! The best for Board B
# chn_toa_threshold_trim = [0, 0, 34, 29, 22, 14, 31, 8, 20, 31, 10, 10, 10, 15, 21, 10, 10, 10, 10, 0, 25, 17, 14, 12, 30, 20, 30, 17, 26, 25, 19, 15, 25, 20, 20, 24, 20, 0, 0, 40, 21, 20, 15, 20, 30, 15, 15, 25, 0, 20, 10, 35, 45, 20, 20, 40, 35, 0, 26, 5, 10, 20, 25, 0, 23, 25, 40, 45, 25, 40, 25, 55, 40, 30, 40, 0, 0, 25, 35, 25, 26, 22, 16, 7, 20, 20, 8, 12, 0, 22, 26, 20, 40, 30, 25, 0, 21, 25, 30, 25, 26, 25, 25, 30, 30, 20, 20, 0, 24, 40, 35, 25, 17, 0, 0, 25, 12, 30, 21, 14, 10, 25, 0, 25, 11, 17, 30, 10, 10, 20, 5, 19, 25, 0, 25, 25, 14, 0, 25, 16, 19, 20, 20, 34, 30, 0, 30, 0, 5, 20, 29, 0]

# ! ToA for Board B 2
#chn_toa_threshold_trim = [0, 1, 1, 0, 10, 10, 10, 10, 1, 5, 5, 10, 10, 10, 10, 0, 10, 5, 10, 0, 5, 5, 20, 10, 5, 10, 1, 10, 10, 5, 5, 20, 10, 0, 5, 5, 0, 0, 0, 0, 10, 0, 0, 0, 0, 1, 5, 5, 10, 5, 5, 5, 20, 0, 20, 20, 10, 0, 0, 0, 1, 5, 5, 10, 20, 10, 10, 1, 0, 10, 5, 5, 10, 10, 10, 0, 0, 10, 10, 10, 10, 10, 10, 10, 0, 5, 0, 0, 0, 5, 5, 1, 0, 0, 10, 0, 5, 5, 0, 1, 10, 10, 5, 10, 10, 10, 20, 10, 10, 5, 10, 10, 20, 0, 0, 0, 5, 0, 10, 10, 10, 5, 0, 5, 0, 0, 0, 0, 10, 0, 10, 10, 10, 0, 10, 0, 20, 10, 10, 0, 10, 5, 10, 5, 20, 5, 10, 10, 10, 20, 0, 0]

# chn_toa_threshold_trim = [0, 21, 11, 0, 15, 30, 15, 15, 11, 10, 15, 20, 15, 20, 30, 1, 0, 15, 0, 0, 0, 0, 0, 0, 10, 20, 6, 20, 20, 6, 15, 40, 20, 10, 15, 10, 0, 0, 0, 0, 20, 0, 0, 0, 1, 6, 5, 6, 15, 5, 10, 15, 30, 10, 10, 25, 20, 0, 5, 10, 6, 10, 15, 15, 40, 0, 15, 0, 5, 20, 15, 10, 30, 30, 0, 0, 0, 15, 20, 15, 15, 15, 15, 15, 1, 10, 0, 1, 5, 6, 15, 6, 0, 0, 20, 0, 15, 10, 10, 2, 15, 0, 10, 15, 20, 15, 0, 20, 20, 10, 11, 15, 40, 0, 0, 0, 10, 0, 0, 20, 15, 10, 5, 15, 5, 0, 0, 0, 0, 10, 15, 0, 0, 0, 0, 0, 25, 15, 15, 0, 0, 15, 20, 0, 10, 15, 0, 20, 0, 30, 0, 0]

# chn_toa_threshold_trim = [0, 21, 16, 5, 25, 35, 20, 16, 6, 15, 5, 15, 5, 10, 40, 21, 10, 25, 1, 0, 5, 10, 10, 5, 20, 20, 7, 25, 25, 16, 15, 35, 20, 15, 15, 20, 10, 0, 0, 0, 30, 0, 0, 0, 11, 16, 25, 16, 20, 15, 20, 25, 30, 15, 20, 26, 15, 0, 15, 15, 16, 20, 5, 25, 30, 20, 16, 20, 5, 20, 25, 11, 30, 35, 10, 0, 0, 25, 10, 25, 25, 15, 25, 15, 21, 20, 20, 11, 15, 16, 35, 16, 5, 0, 25, 0, 14, 30, 15, 7, 25, 10, 20, 35, 21, 20, 10, 20, 30, 30, 31, 15, 40, 0, 0, 0, 11, 0, 5, 21, 15, 10, 6, 16, 5, 0, 0, 0, 0, 0, 5, 10, 5, 0, 0, 1, 35, 20, 16, 0, 0, 16, 25, 10, 15, 0, 10, 20, 10, 35, 0, 0]

# chn_toa_threshold_trim = [0, 21, 21, 15, 35, 30, 30, 16, 16, 15, 15, 25, 0, 11, 35, 31, 15, 25, 6, 0, 15, 11, 11, 10, 21, 21, 7, 25, 30, 26, 16, 35, 20, 25, 25, 30, 20, 0, 0, 0, 31, 0, 0, 0, 31, 26, 30, 17, 25, 25, 30, 30, 40, 14, 20, 25, 10, 0, 15, 20, 21, 21, 15, 30, 40, 30, 16, 30, 0, 20, 25, 12, 30, 30, 20, 0, 0, 26, 10, 5, 35, 15, 20, 15, 26, 30, 30, 21, 20, 26, 45, 26, 0, 0, 30, 0, 15, 40, 25, 6, 26, 15, 40, 55, 22, 21, 30, 20, 40, 40, 32, 25, 50, 0, 0, 0, 11, 0, 10, 22, 15, 10, 1, 16, 5, 0, 1, 1, 0, 0, 4, 11, 10, 0, 5, 0, 30, 21, 11, 0, 0, 16, 30, 11, 15, 0, 10, 20, 11, 25, 0, 0]

# chn_toa_threshold_trim = [0, 21, 26, 20, 36, 30, 31, 21, 26, 16, 25, 24, 0, 11, 34, 36, 20, 25, 11, 0, 20, 11, 12, 10, 21, 26, 17, 26, 35, 27, 26, 35, 25, 30, 30, 20, 20, 0, 0, 0, 32, 0, 0, 0, 36, 27, 35, 18, 30, 25, 35, 40, 35, 14, 25, 30, 5, 0, 25, 25, 21, 26, 10, 30, 20, 10, 26, 10, 0, 20, 20, 7, 31, 35, 10, 0, 0, 36, 10, 10, 45, 25, 30, 16, 26, 40, 29, 31, 20, 31, 50, 31, 10, 0, 35, 0, 16, 40, 26, 6, 27, 10, 45, 60, 23, 21, 30, 30, 45, 45, 37, 24, 45, 0, 0, 10, 12, 0, 10, 22, 20, 15, 11, 17, 5, 0, 0, 1, 5, 5, 4, 16, 15, 0, 10, 5, 30, 20, 10, 0, 0, 15, 35, 12, 15, 20, 11, 20, 16, 30, 0, 0]

while len(chn_toa_threshold_trim) < 152:
    chn_toa_threshold_trim.append(0)

target_chns = []

i2c_setting_verbose = False

toa_target = 50
tot_target = 800

# internal_12b_dac_scan_range = range(500, 2000, 100)
internal_12b_dac_scan_range = range(0, 300, 20)

chn_trim_tot_scan_range = range(0, 64, 2)

# toa_global_threshold_scan_range = range(200, 201, 1)
# toa_trim_scan_range = range(0, 64, 1)

expected_event_num = gen_nr_cycle*(1+machine_gun_val)

if gen_nr_cycle*(1+machine_gun_val)*4 > 300:
    logger.warning("Too much packet requested")

try:
    # * --- Set up channel-wise registers -------------------------------------
    logger.info("Setting up channel-wise registers")
    for _chn in range(152):
        if _chn in dead_channels or _chn in not_used_channels:
            continue

        _asic_num   = _chn // 76
        _chn_num    = _chn % 76
        _half_num   = _chn_num // 38
        _sub_addr   =  packetlib.uni_chn_to_subblock_list[_chn_num]

        _chn_wise = default_channel_wise.copy()
        _chn_wise[0] = inputdac_values[_chn] & 0x3F
        _chn_wise[3] = (trim_dac_values[_chn] << 2) & 0xFC

        if _chn in target_chns:
            _chn_wise[4] = 0x04 # high range
            # _chn_wise[4] = 0x02 # low range
            _chn_wise[2] = (chn_tot_threshold_trim[_chn] & 0x3F) << 2
            _chn_wise[1] = (chn_toa_threshold_trim[_chn] & 0x3F) << 2

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
            logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num}")
     # * --- Set up digital registers ------------------------------------------
    logger.info("Setting up digital registers")
    for _asic_num in range(total_asic):
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=default_digital_half, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Digital_Half_0 settings for ASIC {_asic_num}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=default_digital_half, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Digital_Half_1 settings for ASIC {_asic_num}")
    # * --- Set up global analog registers -------------------------------------
    logger.info("Setting up global analog registers")
    for _asic_num in range(total_asic):
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=default_global_analog, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Global_Analog_0 settings for ASIC {_asic_num}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=default_global_analog, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Global_Analog_1 settings for ASIC {_asic_num}")
    
    scan_val0_max_list = []
    scan_val0_err_list = []
    scan_val1_max_list = []
    scan_val1_err_list = []
    scan_val2_max_list = []
    scan_val2_err_list = []

    progress_bar_12b_dac = tqdm(internal_12b_dac_scan_range)

    scan_chn_pack_num = 38 # so channel from 0 to 23 will be scanned 
    tot_turn_on_point_found = [False]*(scan_chn_pack_num*4)
    toa_turn_on_point_found = [False]*(scan_chn_pack_num*4)

    used_scan_values = []
    tot_turn_on_points = [0]*152
    toa_turn_on_points = [0]*152
    for _12b_dac in progress_bar_12b_dac:
        progress_bar_12b_dac.set_description(f"12b DAC: {_12b_dac}")
        
        used_scan_values.append(_12b_dac)
        for _asic_num in range(total_asic):
            _ref_content_half0  = default_reference_voltage.copy()
            _ref_content_half1  = default_reference_voltage.copy()
            _ref_content_half0[4] = inv_vref_list[_asic_num*2] >> 2
            _ref_content_half1[4] = inv_vref_list[_asic_num*2+1] >> 2
            _ref_content_half0[5] = noinv_vref_list[_asic_num*2] >> 2
            _ref_content_half1[5] = noinv_vref_list[_asic_num*2+1] >> 2
            _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_list[_asic_num*2] & 0x03) << 2) | (noinv_vref_list[_asic_num*2] & 0x03)
            _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_list[_asic_num*2+1] & 0x03) << 2) | (noinv_vref_list[_asic_num*2+1] & 0x03)
            _ref_content_half0[7] = 0x40 | _12b_dac >> 8
            _ref_content_half0[6] = _12b_dac & 0xFF  
            _ref_content_half1[7] = 0x40 | _12b_dac >> 8
            _ref_content_half1[6] = _12b_dac & 0xFF
            _ref_content_half0[3] = toa_global_threshold[_asic_num*2] >> 2
            _ref_content_half1[3] = toa_global_threshold[_asic_num*2+1] >> 2
            _ref_content_half0[2] = tot_global_threshold[_asic_num*2] >> 2
            _ref_content_half1[2] = tot_global_threshold[_asic_num*2+1] >> 2
            _ref_content_half0[1] = (_ref_content_half0[1] & 0x0F) | ((toa_global_threshold[_asic_num*2] & 0x03) << 4) | ((tot_global_threshold[_asic_num*2] & 0x03) << 2)
            _ref_content_half1[1] = (_ref_content_half1[1] & 0x0F) | ((toa_global_threshold[_asic_num*2+1] & 0x03) << 4) | ((tot_global_threshold[_asic_num*2+1] & 0x03) << 2)
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, retry=3, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_0 settings for ASIC {_asic_num}")
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, retry=3, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_1 settings for ASIC {_asic_num}")

        top_content_runLR = top_reg_runLR.copy()
        top_content_runLR[7] = phase_setting & 0x0F
        top_content_offLR = top_reg_offLR.copy()
        top_content_offLR[7] = phase_setting & 0x0F

        time.sleep(0.2)

        if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0x00, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=1, gen_pre_interval=gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle,gen_pre_fcmd=gen_fcmd_internal_injection,gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val, verbose=False):
            logger.warning("Failed to set generator parameters")

        _target_chn_pack = [0,0,0,0]

        val0_mean_list_assembled = np.zeros(152, dtype=int)
        val0_err_list_assembled = np.zeros(152, dtype=int)
        val1_mean_list_assembled = np.zeros(152, dtype=int)
        val1_err_list_assembled = np.zeros(152, dtype=int)
        val2_mean_list_assembled = np.zeros(152, dtype=int)
        val2_err_list_assembled = np.zeros(152, dtype=int)

        for _chn in range(0, scan_chn_pack_num*4, 4):
            # logger.debug(f"Channel pack: {_chn}")
            _target_chn_pack = [_chn, _chn+1, _chn+2, _chn+3]

            for _chn_index, _chn in enumerate(_target_chn_pack):
                if _chn not in dead_channels and _chn not in not_used_channels:
                    _sub_addr =  packetlib.uni_chn_to_subblock_list[_chn%76]
                    _asic_num = _chn // 76
                    _chn_wise = default_channel_wise.copy()
                    _chn_wise[0] = inputdac_values[_chn] & 0x3F
                    _chn_wise[3] = (trim_dac_values[_chn] << 2) & 0xFC
                    _chn_wise[4] = 0x04 # high range
                    _chn_wise[2] = (chn_tot_threshold_trim[_chn] & 0x3F) << 2
                    _chn_wise[1] = (chn_toa_threshold_trim[_chn] & 0x3F) << 2
                    if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                        logger.warning(f"Failed to set Channel Wise settings for {_chn}")

            val0_mean_list, val0_err_list, val1_mean_list, val1_err_list, val2_mean_list, val2_err_list = measure_v0v1v2(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_content_runLR, top_content_offLR, expected_event_num, 5, logger)
            # logger.debug(f"Scan value: {val0_mean_list}")

            for _chn_index, _chn in enumerate(_target_chn_pack):
                if _chn not in dead_channels and _chn not in not_used_channels:
                    _sub_addr =  packetlib.uni_chn_to_subblock_list[_chn%76]
                    _asic_num = _chn // 76
                    _chn_wise = default_channel_wise.copy()
                    _chn_wise[0] = inputdac_values[_chn] & 0x3F
                    _chn_wise[3] = (trim_dac_values[_chn] << 2) & 0xFC
                    _chn_wise[4] = 0x00 # trun off high range
                    _chn_wise[2] = (chn_tot_threshold_trim[_chn] & 0x3F) << 2
                    _chn_wise[1] = (chn_toa_threshold_trim[_chn] & 0x3F) << 2
                    if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                        logger.warning(f"Failed to set Channel Wise settings for {_chn}")

            for _chn_index, _chn in enumerate(_target_chn_pack):
                if _chn not in dead_channels and _chn not in not_used_channels:
                    val0_mean_list_assembled[_chn] = val0_mean_list[_chn]
                    val0_err_list_assembled[_chn] = val0_err_list[_chn]
                    val1_mean_list_assembled[_chn] = val1_mean_list[_chn]
                    val1_err_list_assembled[_chn] = val1_err_list[_chn]
                    val2_mean_list_assembled[_chn] = val2_mean_list[_chn]
                    val2_err_list_assembled[_chn] = val2_err_list[_chn]


        scan_val0_max_list.append(val0_mean_list_assembled)
        scan_val0_err_list.append(val0_err_list_assembled)
        scan_val1_max_list.append(val1_mean_list_assembled)
        scan_val1_err_list.append(val1_err_list_assembled)
        scan_val2_max_list.append(val2_mean_list_assembled)
        scan_val2_err_list.append(val2_err_list_assembled)
        # logger.debug(f"Scan value: {val0_mean_list}")

        # find if the toa/tot is turned on: three 0s followed by three 1s
        for _interested_chn_index, _interested_chn in enumerate(range(0, scan_chn_pack_num*4)):
            if _interested_chn in dead_channels or _interested_chn in not_used_channels:
                continue
            if len(scan_val1_max_list) >= 3 and not tot_turn_on_point_found[_interested_chn_index]:
                _last_3_val_lists = scan_val1_max_list[-3:]
                _last_3_vals = []
                for _val_list in _last_3_val_lists:
                    _tot_val = int(_val_list[_interested_chn])
                    if (_tot_val >> 9) & 0x1 == 1:
                        _tot_val = (_tot_val&0x1FF) << 3
                    _last_3_vals.append(_tot_val)
                _over_zero_cnt = 0
                for _val in _last_3_vals:
                    if _val > 0:
                        _over_zero_cnt += 1
                if _over_zero_cnt >= 2:
                    logger.info(f"Found the turn-on point of ToT at 12b DAC: {_12b_dac} for channel {_interested_chn}")
                    correspoding_adc_val = scan_val0_max_list[-3][_interested_chn]
                    correspoding_adc_val_net = correspoding_adc_val - pedestal_value
                    logger.info(f"Corresponding ADC value: {correspoding_adc_val}, net ADC value: {correspoding_adc_val_net}")
                    tot_turn_on_point_found[_interested_chn_index] = True
                    tot_turn_on_points[_interested_chn] = correspoding_adc_val_net
            if len(scan_val2_max_list) >= 3 and not toa_turn_on_point_found[_interested_chn_index]:
                _last_3_val_lists = scan_val2_max_list[-3:]
                _last_3_vals = []
                for _val_list in _last_3_val_lists:
                    _last_3_vals.append(_val_list[_interested_chn])
                _over_zero_cnt = 0
                for _val in _last_3_vals:
                    if _val > 0:
                        _over_zero_cnt += 1
                if _over_zero_cnt >= 2:
                    logger.info(f"Found the turn-on point of ToA at 12b DAC: {_12b_dac} for channel {_interested_chn}")
                    correspoding_adc_val = scan_val0_max_list[-3][_interested_chn]
                    correspoding_adc_val_net = correspoding_adc_val - pedestal_value
                    logger.info(f"Corresponding ADC value: {correspoding_adc_val}, net ADC value: {correspoding_adc_val_net}")
                    toa_turn_on_point_found[_interested_chn_index] = True
                    toa_turn_on_points[_interested_chn] = correspoding_adc_val_net

            
        if all(tot_turn_on_point_found) and all(toa_turn_on_point_found):
            break

    tot_turn_on_points_half_mean  = [0,0,0,0]
    toa_turn_on_points_half_mean  = [0,0,0,0]
    tot_turn_on_points_half_std   = [0,0,0,0]
    toa_turn_on_points_half_std   = [0,0,0,0]
    tot_turn_on_points_count = [0,0,0,0]
    toa_turn_on_points_count = [0,0,0,0]

    for _chn in range(0, scan_chn_pack_num*4):
        if _chn in dead_channels or _chn in not_used_channels:
            continue
        _half = _chn // 38
        tot_turn_on_points_half_mean[_half] += tot_turn_on_points[_chn]
        toa_turn_on_points_half_mean[_half] += toa_turn_on_points[_chn]
        tot_turn_on_points_count[_half] += 1
        toa_turn_on_points_count[_half] += 1
    
    for _half in range(4):
        tot_turn_on_points_half_mean[_half] /= tot_turn_on_points_count[_half]
        toa_turn_on_points_half_mean[_half] /= toa_turn_on_points_count[_half]
    
    for _chn in range(0, scan_chn_pack_num*4):
        if _chn in dead_channels or _chn in not_used_channels:
            continue
        _half = _chn // 38
        tot_turn_on_points_half_std[_half] += (tot_turn_on_points[_chn] - tot_turn_on_points_half_mean[_half])**2
        toa_turn_on_points_half_std[_half] += (toa_turn_on_points[_chn] - toa_turn_on_points_half_mean[_half])**2

    for _half in range(4):
        tot_turn_on_points_half_std[_half] = np.sqrt(tot_turn_on_points_half_std[_half]/tot_turn_on_points_count[_half])
        toa_turn_on_points_half_std[_half] = np.sqrt(toa_turn_on_points_half_std[_half]/toa_turn_on_points_count[_half])

    logger.info(f"Averaged ToT turn-on points: {tot_turn_on_points_half_mean}")
    logger.info(f"Averaged ToA turn-on points: {toa_turn_on_points_half_mean}")
    logger.info(f"Standard deviation of ToT turn-on points: {tot_turn_on_points_half_std}")
    logger.info(f"Standard deviation of ToA turn-on points: {toa_turn_on_points_half_std}")

    fig_tot, ax_tot = plt.subplots(1, 1, figsize=(14, 6), dpi=300)
    fig_toa, ax_toa = plt.subplots(1, 1, figsize=(14, 6), dpi=300)

    ax_tot.errorbar(range(0, scan_chn_pack_num*4), tot_turn_on_points, yerr=0, fmt='o', label='ToT turn-on points')
    ax_tot.set_xlabel("Channel number")
    ax_tot.set_ylabel("ADC value")
    ax_tot.set_title("ToT turn-on points")
    ax_tot.legend()
    # add vertical lines for ten channels
    for i in range(0, scan_chn_pack_num*4, 10):
        ax_tot.axvline(x=i, color='gray', linestyle='--')
    # add horizontal line for tot target
    ax_tot.axhline(y=tot_target, color='red', linestyle='--')

    ax_toa.errorbar(range(0, scan_chn_pack_num*4), toa_turn_on_points, yerr=0, fmt='o', label='ToA turn-on points')
    ax_toa.set_xlabel("Channel number")
    ax_toa.set_ylabel("ADC value")
    ax_toa.set_title("ToA turn-on points")
    ax_toa.legend()
    # add vertical lines for ten channels
    for i in range(0, scan_chn_pack_num*4, 10):
        ax_toa.axvline(x=i, color='gray', linestyle='--')
    ax_toa.axhline(y=toa_target, color='red', linestyle='--')

    fig_tot.savefig(os.path.join(output_data_path, f"tot_turn_on_points.png"))
    fig_toa.savefig(os.path.join(output_data_path, f"toa_turn_on_points.png"))
    

finally:
    logger.info("Closing UDP socket")
    socket_udp.close()

diff_list = []
for _val in tot_turn_on_points:
    diff_list.append(_val - tot_target)

for _index, _val in enumerate(diff_list):
    if _index in dead_channels or _index in not_used_channels:
        continue
    if _val > 40:
        chn_tot_threshold_trim[_index] += 20
    elif _val > 20:
        chn_tot_threshold_trim[_index] += 10
    elif _val > 10:
        chn_tot_threshold_trim[_index] += 5
    elif _val > 5:
        chn_tot_threshold_trim[_index] += 1
    elif _val < -40:
        chn_tot_threshold_trim[_index] -= 20
    elif _val < -20:
        chn_tot_threshold_trim[_index] -= 10
    elif _val < -10:
        chn_tot_threshold_trim[_index] -= 5
    elif _val < -5:
        chn_tot_threshold_trim[_index] -= 1

    if chn_tot_threshold_trim[_index] < 0:
        chn_tot_threshold_trim[_index] = 0
    elif chn_tot_threshold_trim[_index] > 63:
        chn_tot_threshold_trim[_index] = 63

logger.info(f"Proposed ToT threshold trim: {chn_tot_threshold_trim}")
logger.info(f"Difference list: {diff_list}")

diff_list = []
for _val in toa_turn_on_points:
    diff_list.append(_val - toa_target)

for _index, _val in enumerate(diff_list):
    if _index in dead_channels or _index in not_used_channels:
        continue
    if _val > 40:
        chn_toa_threshold_trim[_index] += 20
    elif _val > 20:
        chn_toa_threshold_trim[_index] += 10
    elif _val > 10:
        chn_toa_threshold_trim[_index] += 5
    elif _val > 5:
        chn_toa_threshold_trim[_index] += 1
    elif _val < -40:
        chn_toa_threshold_trim[_index] -= 20
    elif _val < -20:
        chn_toa_threshold_trim[_index] -= 10
    elif _val < -10:
        chn_toa_threshold_trim[_index] -= 5
    elif _val < -5:
        chn_toa_threshold_trim[_index] -= 1

    if chn_toa_threshold_trim[_index] < 0:
        chn_toa_threshold_trim[_index] = 0
    elif chn_toa_threshold_trim[_index] > 63:
        chn_toa_threshold_trim[_index] = 63

logger.info(f"Proposed ToA threshold trim: {chn_toa_threshold_trim}")

logger.info(f"Difference list: {diff_list}")
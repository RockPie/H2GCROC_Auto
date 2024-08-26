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
script_id_str       = '204_PhaseScan'
script_version_str  = '0.1'

# * --- Test function -------------------------------------------------

def measure_v0v1v2_raw(_socket_udp, _ip, _port, _fpga_address, _reg_runLR, _reg_offLR, _event_num, _fragment_life, _logger):
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
    
    return all_chn_value_0_array, all_chn_value_1_array, all_chn_value_2_array

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
default_reference_voltage[10] = 0x00 # choice_cinj

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
if len(pedestal_calib_files) > 0:
    newest_pedestal_calib_file = pedestal_calib_files[0]
    logger.info(f"Found newest pedestal calibration file: {newest_pedestal_calib_file}")

trim_dac_values     = []
inputdac_values     = []
noinv_vref_list     = []
inv_vref_list       = []
dead_channels       = []
not_used_channels   = []

with open(os.path.join(pedestal_calib_folder, newest_pedestal_calib_file), 'r') as json_file:
    pedestal_calib      = json.load(json_file)
    noinv_vref_list     = pedestal_calib["noinv_vref_list"]
    inv_vref_list       = pedestal_calib["inv_vref_list"]
    trim_dac_values     = pedestal_calib["chn_trim_settings"]
    inputdac_values     = pedestal_calib["chn_inputdac_settings"]
    dead_channels       = pedestal_calib["dead_channels"]
    not_used_channels   = pedestal_calib["channel_not_used"]

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
gen_nr_cycle                = 1
gen_interval_value          = 100

_12b_dac      = 500

toa_global_threshold = 150
tot_global_threshold = 150

target_chns = [1]

i2c_setting_verbose = False

gen_pre_interval_scan_range = range(17, 20, machine_gun_val+1)
phase_scan_range = range(11, 16)

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
        _sub_addr   =  packetlib.uni_chn_to_subblock_list[_chn_num]

        _chn_wise = default_channel_wise.copy()
        _chn_wise[0] = inputdac_values[_chn] & 0x3F
        _chn_wise[3] = (trim_dac_values[_chn] << 2) & 0xFC

        if _chn in target_chns:
            # _chn_wise[4] = 0x04 # high range
            _chn_wise[4] = 0x02 # low range
            # _chn_wise[1] = 0xF0 # toa threshold trim
            # _chn_wise[2] = 0xF0 # tot threshold trim

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
        _ref_content_half0[3] = toa_global_threshold >> 2
        _ref_content_half1[3] = toa_global_threshold >> 2
        _ref_content_half0[2] = tot_global_threshold >> 2
        _ref_content_half1[2] = tot_global_threshold >> 2
        _ref_content_half0[1] = (_ref_content_half0[1] & 0x0F) | ((toa_global_threshold & 0x03) << 4) | ((tot_global_threshold & 0x03) << 2)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0x0F) | ((toa_global_threshold & 0x03) << 4) | ((tot_global_threshold & 0x03) << 2)
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_0 settings for ASIC {_asic_num}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_1 settings for ASIC {_asic_num}")

    
    scan_val0_max_list = []
    scan_val0_err_list = []
    scan_val1_max_list = []
    scan_val1_err_list = []
    scan_val2_max_list = []
    scan_val2_err_list = []

    chns_phase_list = [[]]*len(target_chns)
    chns_pre_interval_list = [[]]*len(target_chns)
    chns_val0_list = [[]]*len(target_chns)
    
    progress_bar_phase = tqdm(phase_scan_range, desc="Phase scan", leave=True)
    for _phase in progress_bar_phase:
        progress_bar_phase.set_description(f"Phase scan: {_phase}")
        _top_content_runLR = top_reg_runLR.copy()
        _top_content_runLR[7] = _phase
        _top_content_offLR = top_reg_offLR.copy()
        _top_content_offLR[7] = _phase
        progress_bar_gen_pre_interval = tqdm(gen_pre_interval_scan_range, desc="Pre-interval scan", leave=False)
        for _gen_pre_interval in progress_bar_gen_pre_interval:
            for _retry in range(3):
                time.sleep(0.1)
                if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0x00, fpga_addr=fpga_address, data_coll_en=0x03,trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=1, gen_pre_interval= _gen_pre_interval, gen_nr_of_cycle=gen_nr_cycle,gen_pre_fcmd=gen_fcmd_internal_injection,gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val, verbose=False):
                    logger.warning("Failed to set generator parameters")

                all_chn_value_0_array, all_chn_value_1_array, all_chn_value_2_array = measure_v0v1v2_raw(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, _top_content_runLR, _top_content_offLR, expected_event_num, 5, logger)

                for _chn_index, _chn in enumerate(target_chns):
                    if _chn in dead_channels or _chn in not_used_channels:
                        continue
                    _val0_list = []
                    for _event in range(expected_event_num):
                        _val0_list.append(all_chn_value_0_array[_event][_chn])
                    chns_val0_list[_chn_index].append(_val0_list)
                    chns_phase_list[_chn_index].append(_phase)
                    chns_pre_interval_list[_chn_index].append(_gen_pre_interval)

finally:
    socket_udp.close()
    logger.info("Socket closed")

fig_phase, ax_phase = plt.subplots(1,1, figsize=(10, 6), dpi=200)
for _chn_index, _chn in enumerate(target_chns):
    x_vals = []
    y_vals = []
    for _index, _val in enumerate(chns_val0_list[_chn_index]):
        _phase_offset = chns_phase_list[_chn_index][_index] - 8
        if _phase_offset < 0:
            _phase_offset += 16
        _phase_offset *= (1.0 / 16.0)
        _pre_interval_offset = chns_pre_interval_list[_chn_index][_index]
        for _v_index, _v in enumerate(_val):
            x_vals.append(_v_index + _pre_interval_offset + _phase_offset)
            y_vals.append(_v)
    ax_phase.scatter(x_vals, y_vals, label=f"Chn {_chn}", s=4, alpha=0.5)

ax_phase.set_xlabel("Time [25 ns]")
ax_phase.set_ylabel("ADC value")

plt.savefig(os.path.join(output_data_path, f"phase_scan.png"))
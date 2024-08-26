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

# * --- Set up script information -------------------------------------
script_id_str       = '106_ToA_ToT_Scan'
script_version_str  = '0.1'

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
default_reference_voltage[10] = 0x40

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
noinv_vref_list     = []
inv_vref_list       = []

with open(os.path.join(pedestal_calib_folder, newest_pedestal_calib_file), 'r') as json_file:
    pedestal_calib      = json.load(json_file)
    noinv_vref_list     = pedestal_calib["noinv_vref_list"]
    inv_vref_list       = pedestal_calib["inv_vref_list"]
    trim_dac_values     = pedestal_calib["chn_trim_settings"]

if len(noinv_vref_list) == 0 or len(inv_vref_list) == 0 or len(trim_dac_values) == 0:
    logger.critical("Pedestal calibration file format is incorrect")
    exit()

# * --- Set running parameters ------------------------------------------------
total_asic          = 2
fpga_address        = 0x00

machine_gun_val             = 9
gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011
gen_pre_inverval_value      = 15
gen_nr_cycle                = 1
gen_interval_value          = 100
# internal_12b_dac_value      = 0x0FFF
repeat_times                = 1
toa_global_threshold = 200
tot_global_threshold = 200
target_chns = [1, 2, 3, 4, 5]

i2c_setting_verbose = False

internal_12b_dac_scan_range = range(0, 4096, 256)

if gen_nr_cycle*(1+machine_gun_val)*4 > 300:
    logger.warning("Too much packet requested")

try:
    # * --- Set up channel-wise registers -------------------------------------
    logger.info("Setting up channel-wise registers")
    for _chn in range(152):
        _asic_num   = _chn // 76
        _chn_num    = _chn % 76
        _half_num   = _chn_num // 38
        _sub_addr   =  packetlib.uni_chn_to_subblock_list[_chn_num]

        _chn_content = default_channel_wise.copy()
        _chn_content[3] = int(trim_dac_values[_chn]) << 2

        if _chn in target_chns:
            _chn_content[4] = 0x04 # high range

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set ChannelWise settings for ASIC {_asic_num}")
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
    # * --- Set up reference voltage registers ---------------------------------
    # logger.info("Setting up reference voltage registers")
    # for _asic_num in range(total_asic):
    #     _ref_content_half0  = default_reference_voltage.copy()
    #     _ref_content_half1  = default_reference_voltage.copy()
    #     _ref_content_half0[4] = inv_vref_list[_asic_num*2] >> 2
    #     _ref_content_half1[4] = inv_vref_list[_asic_num*2+1] >> 2
    #     _ref_content_half0[5] = noinv_vref_list[_asic_num*2] >> 2
    #     _ref_content_half1[5] = noinv_vref_list[_asic_num*2+1] >> 2
    #     _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_list[_asic_num*2] & 0x03) << 2) | (noinv_vref_list[_asic_num*2] & 0x03)
    #     _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_list[_asic_num*2+1] & 0x03) << 2) | (noinv_vref_list[_asic_num*2+1] & 0x03)
    #     _ref_content_half0[7] = 0x40 | internal_12b_dac_value >> 8
    #     _ref_content_half0[6] = internal_12b_dac_value & 0xFF  
    #     _ref_content_half1[7] = 0x40 | internal_12b_dac_value >> 8
    #     _ref_content_half1[6] = internal_12b_dac_value & 0xFF
    #     _ref_content_half0[3] = toa_global_threshold >> 2
    #     _ref_content_half1[3] = toa_global_threshold >> 2
    #     _ref_content_half0[1] = (_ref_content_half0[1] & 0xCF) | ((toa_global_threshold & 0x03) << 4)
    #     _ref_content_half1[1] = (_ref_content_half1[1] & 0xCF) | ((toa_global_threshold & 0x03) << 4)
    #     if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, retry=3, verbose=i2c_setting_verbose):
    #         logger.warning(f"Failed to set Reference_Voltage_0 settings for ASIC {_asic_num}")
    #     if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, retry=3, verbose=i2c_setting_verbose):
    #         logger.warning(f"Failed to set Reference_Voltage_1 settings for ASIC {_asic_num}")

    # * --- Set up scanning ---------------------------------------------------
    # progress_bar_toa_global_scan = tqdm(toa_global_threshold_scan_range, leave=True)
    # for _toa_global in progress_bar_toa_global_scan:
    #     progress_bar_toa_global_scan.set_description(f'ToA Global {_toa_global}')
    #     progress_bar_toa_trim_scan = tqdm(toa_trim_scan_range, leave=False)
        # for _toa_trim in progress_bar_toa_trim_scan:
        #     progress_bar_toa_trim_scan.set_description(f'ToA Trim {_toa_trim}')
    progress_bar_internal_12b_dac_scan = tqdm(internal_12b_dac_scan_range, leave=True)
    for internal_12b_dac_value in progress_bar_internal_12b_dac_scan:
        progress_bar_internal_12b_dac_scan.set_description(f'Internal 12b DAC {internal_12b_dac_value}')
        if True:
            output_data_txt_name = script_id_str + "_internal_" + str(internal_12b_dac_value) +  "_data_" + time.strftime("%Y%m%d_%H%M%S") + ".txt"
            output_data_txt_path = os.path.join(output_data_path, output_data_txt_name)
            measurement_good_array = []
            with open(output_data_txt_path, 'w') as output_data_txt:
                for _asic_num in range(total_asic):
                    _ref_content_half0  = default_reference_voltage.copy()
                    _ref_content_half1  = default_reference_voltage.copy()
                    _ref_content_half0[4] = inv_vref_list[_asic_num*2] >> 2
                    _ref_content_half1[4] = inv_vref_list[_asic_num*2+1] >> 2
                    _ref_content_half0[5] = noinv_vref_list[_asic_num*2] >> 2
                    _ref_content_half1[5] = noinv_vref_list[_asic_num*2+1] >> 2
                    _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_list[_asic_num*2] & 0x03) << 2) | (noinv_vref_list[_asic_num*2] & 0x03)
                    _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_list[_asic_num*2+1] & 0x03) << 2) | (noinv_vref_list[_asic_num*2+1] & 0x03)
                    _ref_content_half0[7] = 0x40 | internal_12b_dac_value >> 8
                    _ref_content_half0[6] = internal_12b_dac_value & 0xFF  
                    _ref_content_half1[7] = 0x40 | internal_12b_dac_value >> 8
                    _ref_content_half1[6] = internal_12b_dac_value & 0xFF
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

                # for _chn in range(152):
                #     if _chn in target_chns:
                #         _asic_num   = _chn // 76
                #         _chn_num    = _chn % 76
                #         _half_num   = _chn_num // 38
                #         _sub_addr   =  packetlib.uni_chn_to_subblock_list[_chn_num]
                #         _chn_content = default_channel_wise.copy()
                #         _chn_content[3] = int(trim_dac_values[_chn]) << 2

                #         _chn_content[4] = 0x02
                #         _chn_content[1] = _toa_trim << 2

                #         if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, retry=3, verbose=i2c_setting_verbose):
                #             logger.warning(f"Failed to set ChannelWise settings for ASIC {_asic_num}")

                # set generator parameters
                if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0x00, fpga_addr=fpga_address, data_coll_en=0x03,trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=1, gen_pre_interval = gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle,gen_pre_fcmd=gen_fcmd_internal_injection,gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val, verbose=False):
                    logger.warning("Failed to set generator parameters")

                for _repeat in range(repeat_times):
                    _top_content = top_reg_runLR.copy()
                    for _asic in range(total_asic):
                        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address,sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=_top_content, retry=3, verbose=i2c_setting_verbose):
                            logger.warning(f"Failed to set Top settings to runLR for ASIC {_asic}")
                    if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00,gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
                        logger.warning("Failed to start generator")
                    extracted_payloads_pool = []
                    event_fragment_pool     = []
                    measurement_good_flag = True
                    expected_half_packet_num = gen_nr_cycle * (machine_gun_val+1) * 4
                    expected_event_num = gen_nr_cycle * (machine_gun_val+1) 
                    current_half_packet_num = 0
                    current_event_num = 0
                    all_chn_value_0_array = np.zeros((expected_event_num, 152))
                    all_chn_value_1_array = np.zeros((expected_event_num, 152))
                    all_chn_value_2_array = np.zeros((expected_event_num, 152))
                    hamming_code_array = np.zeros((expected_event_num, 12))
                    # logger.info("Start reading data")
                    # ! Core code for reading --------------------------------------------------------
                    while True:
                        try:
                            # logger.debug("Waiting for packet")
                            data_packet, rec_addr    = socket_udp.recvfrom(8192)
                            # logger.debug("Packet received")
                            extracted_payloads_pool += packetlib.extract_raw_payloads(data_packet)
                            while len(extracted_payloads_pool) >= 5:
                                candidate_packet_lines = extracted_payloads_pool[:5]
                                is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
                                if is_packet_good:
                                    event_fragment_pool.append(event_fragment)
                                    current_half_packet_num += 1
                                    extracted_payloads_pool = extracted_payloads_pool[5:]
                                    # have space between bytes
                                    for _byte_line in event_fragment:
                                        hex_data = ' '.join([f'{_byte:02X}' for _byte in _byte_line])
                                        output_data_txt.write(hex_data + '\n')
                                else:
                                    logger.warning("Event fragment is not good")
                                    extracted_payloads_pool = extracted_payloads_pool[1:]
                            indices_to_delete = set()
                            if len(event_fragment_pool) >= 4:
                                event_fragment_pool = sorted(event_fragment_pool, key=lambda x: x[0][3:7])
                            i = 0
                            while i <= len(event_fragment_pool) - 4:
                                timestamp0 = event_fragment_pool[i][0][4] << 24 | event_fragment_pool[i][0][5] << 16 | event_fragment_pool[i][0][6] << 8 |event_fragment_pool[i][0][7]
                                timestamp1 = event_fragment_pool[i+1][0][4] << 24 | event_fragment_pool[i+1][0][5] << 16 | event_fragment_pool[i+1][0][6] << 8 |event_fragment_pool[i+1][0][7]
                                timestamp2 = event_fragment_pool[i+2][0][4] << 24 | event_fragment_pool[i+2][0][5] << 16 | event_fragment_pool[i+2][0][6] << 8 |event_fragment_pool[i+2][0][7]
                                timestamp3 = event_fragment_pool[i+3][0][4] << 24 | event_fragment_pool[i+3][0][5] << 16 | event_fragment_pool[i+3][0][6] << 8 |event_fragment_pool[i+3][0][7]
                                if timestamp0 == timestamp1 and timestamp0 == timestamp2 and timestamp0 == timestamp3:
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
                                    i += 1
                            for index in sorted(indices_to_delete, reverse=True):
                                del event_fragment_pool[index]
                            # logger.debug("current event num:" + str(current_event_num))
                            if current_event_num == expected_event_num:
                                break;
                        except Exception as e:
                            logger.warning("Exception in receiving data")
                            logger.warning(e)
                            logger.warning('Packet expected: ' + str(expected_half_packet_num))
                            logger.warning('Packet received: ' + str(current_half_packet_num))
                            logger.warning('left fragments:' + str(len(event_fragment_pool)))
                            logger.warning("current event num:" + str(current_event_num))
                            measurement_good_flag = False
                            break
                    if not np.all(hamming_code_array == 0):
                        print("Hamming code error!")
                        measurement_good_flag = False
                    measurement_good_array.append(measurement_good_flag)
                    if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00,gen_start_stop=0, daq_start_stop=0x00, verbose=False):
                        print('\033[33m' + "Warning in sending DAQ Push" + '\033[0m')
                    _top_content = top_reg_offLR.copy()
                    for _asic in range(2):
                        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address,sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=_top_content, retry=3, verbose=False):
                            print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(_asic) + '\033[0m')

finally:
    logger.info("Closing UDP socket")
    socket_udp.close()
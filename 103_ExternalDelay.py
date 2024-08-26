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
script_id_str       = '103_ExternalDelay'
script_version_str  = '0.2'

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
timeout         = 1 # seconds

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
# socket_udp.settimeout(timeout)

# * I2C register settings
# * ---------------------------------------------------------------------------
i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

top_reg_runLR = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
top_reg_offLR = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
HV_on         = [0xA0,0x01, 0x03, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
while len(HV_on) < 40:
    HV_on.append(0x00)
# HV_on_second = [0xA0,0x01, 0x03, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
# while len(HV_on_second) < 40:
#     HV_on_second.append(0x00)

default_global_analog   = reg_settings.get_default_reg_content('registers_global_analog')
default_global_analog[8]  = 0xA0
default_global_analog[9]  = 0xCA
default_global_analog[10] = 0x42
default_global_analog[14] = 0x6F

default_channel_wise    = reg_settings.get_default_reg_content('registers_channel_wise')
default_channel_wise[14] = 0xC0

default_reference_voltage = reg_settings.get_default_reg_content('registers_reference_voltage')
default_reference_voltage[10] = 0x07

default_digital_half = reg_settings.get_default_reg_content('registers_digital_half')
default_digital_half[4] = 0xC0
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
fpga_address        = int(h2gcroc_ip.split('.')[-1]) - 208  # it is following the IP address of the H2GCROC
fragment_life       = 5

machine_gun_val             = 9
gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011

ex_trg_delay_trg_max = 100

gen_pre_inverval_value      = 200
gen_nr_cycle                = 1
gen_interval_value          = 100

i2c_setting_verbose = False

L1_offset_scan_range    = range(0, 31, (machine_gun_val + 1))
ex_trg_scan_range       = range(0, 31, 10)

_ex_trg_val = 2 # TODO: Fixed external trigger value
# _L1_delay_value = 0 # TODO: Fixed L1 delay value

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
    logger.info("Setting up reference voltage registers")
    for _asic_num in range(total_asic):
        _ref_content_half0  = default_reference_voltage.copy()
        _ref_content_half1  = default_reference_voltage.copy()
        _ref_content_half0[4] = inv_vref_list[_asic_num*2] >> 2
        _ref_content_half1[4] = inv_vref_list[_asic_num*2+1] >> 2
        _ref_content_half0[5] = noinv_vref_list[_asic_num*2] >> 2
        _ref_content_half1[5] = noinv_vref_list[_asic_num*2+1] >> 2
        _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_list[_asic_num*2] & 0x03) << 2) | (noinv_vref_list[_asic_num*2] & 0x03)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_list[_asic_num*2+1] & 0x03) << 2) | (noinv_vref_list[_asic_num*2+1] & 0x03)
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_0 settings for ASIC {_asic_num}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_1 settings for ASIC {_asic_num}")

    # * --- Set up HV ---------------------------------------------------------
    logger.info("Setting up HV")
    socket_udp.sendto(bytes(HV_on), (h2gcroc_ip, h2gcroc_port))

    # * --- Do the scan -------------------------------------------------------
    progress_bar = tqdm(L1_offset_scan_range)
    # progress_bar = tqdm(ex_trg_scan_range)
    measurement_good_array = []
    for _L1_delay_value in progress_bar:
    # for _ex_trg_val in progress_bar:
        progress_bar.set_description(f"L1 delay: {_L1_delay_value}")
        output_data_txt_name = "ex_delay_scan_data_val_" + str(_L1_delay_value) + "_" + time.strftime("%Y%m%d_%H%M%S") + ".txt"
        output_data_txt_path = os.path.join(output_data_path, output_data_txt_name)
        with open(output_data_txt_path, 'w') as data_file:
            _trg_dead_time = _ex_trg_val + machine_gun_val + 10
            if _trg_dead_time > 255:
                logger.warning("Trigger dead time is too long")
                _trg_dead_time = 255
            # set up L1 offset
            for _asic in range(total_asic):
                _digital_content = default_digital_half.copy()
                _digital_content[15] = _L1_delay_value
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_content, retry=3, verbose=i2c_setting_verbose):
                    logger.warning(f"Failed to set L1 delay value {_L1_delay_value} for ASIC {_asic} for half 0")
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=_digital_content, retry=3, verbose=i2c_setting_verbose):
                    logger.warning(f"Failed to set L1 delay value {_L1_delay_value} for ASIC {_asic} for half 1")

            if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=0, gen_pre_interval = gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=gen_fcmd_internal_injection,ext_trg_en=1, ext_trg_delay=_ex_trg_val, ext_trg_deadtime=255, gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val,verbose=False):
                logger.warning(f"Failed to set up the generator for L1 delay value {_L1_delay_value}")

            packetlib.clean_socket(socket_udp)

            # set up top registers
            for _asic in range(total_asic):
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=3, verbose=i2c_setting_verbose):
                    logger.warning(f"Failed to set Top settings RunLR for ASIC {_asic} for run")

            # start generator
            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0xFF, verbose=False):
                logger.warning(f"Failed to start generator for L1 delay value {_L1_delay_value}")

            extracted_payloads_pool = []
            event_fragment_pool     = []
            fragment_life_dict      = {}

            expected_half_packet_num = ex_trg_delay_trg_max * (machine_gun_val + 1) * 4
            expected_event_num = ex_trg_delay_trg_max * (machine_gun_val + 1)
            current_half_packet_num = 0
            current_event_num = 0

            all_chn_value_0_array = np.zeros((expected_event_num, 152))
            all_chn_value_1_array = np.zeros((expected_event_num, 152))
            all_chn_value_2_array = np.zeros((expected_event_num, 152))
            hamming_code_array = np.zeros((expected_event_num, 12))

            measurement_good_flag = True

            _pool_1_depth = 0
            _pool_2_depth = 0

            # ! Core code for reading --------------------------------------------------------
            while True:
                try:
                    data_packet, rec_addr    = socket_udp.recvfrom(8192)
                    extracted_payloads_pool += packetlib.extract_raw_payloads(data_packet)
                    while len(extracted_payloads_pool) >= 5:
                        candidate_packet_lines = extracted_payloads_pool[:5]
                        is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
                        if is_packet_good:
                            event_fragment_pool.append(event_fragment)
                            current_half_packet_num += 1
                            # _line_counter += 1
                            extracted_payloads_pool = extracted_payloads_pool[5:]
                            hex_data = ' '.join(b.hex() for b in event_fragment)
                            data_file.write(hex_data + '\n')
                        else:
                            logger.warning("Event fragment is not good")
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
                                if fragment_life_dict[timestamp0] >= fragment_life - 1:
                                    indices_to_delete.update([i])
                                    del fragment_life_dict[timestamp0]
                                    print(f"Fragment life expired: {timestamp0}")
                                else:
                                    fragment_life_dict[timestamp0] += 1
                            else:
                                fragment_life_dict[timestamp0] = 1
                            i += 1
                    _pool_2_depth = len(event_fragment_pool)
                    for index in sorted(indices_to_delete, reverse=True):
                        del event_fragment_pool[index]
                    print(f"Current fragment pool size: {len(event_fragment_pool)}")
                    if current_event_num % 100 == 0:
                        logger.info(f"Current event number: {current_event_num}")
                        logger.info(f"Current pool 1 depth: {_pool_1_depth}")
                        logger.info(f"Current pool 2 depth: {_pool_2_depth}")
                    if current_event_num == expected_event_num:
                        break;
                        
                except Exception as e:
                    logger.warning("Exception in receiving data")
                    logger.warning(e)
                    logger.warning(f"Packet expected: {expected_half_packet_num}")
                    logger.warning(f"Packet received: {current_half_packet_num}")
                    logger.warning(f"Left fragments: {len(event_fragment_pool)}")
                    logger.warning(f"Current event num: {current_event_num}")
                    measurement_good_flag = False
                    break

            # check if hamming code is all 0
            if not np.all(hamming_code_array == 0):
                logger.warning("Hamming code error!")
                measurement_good_flag = False

            measurement_good_array.append(measurement_good_flag)
            # ! Core code finish -------------------------------------------------------------

            # stop generator
            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
                logger.warning(f"Failed to start generator for L1 delay value {_L1_delay_value}")

            # set up top registers
            for _asic in range(total_asic):
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=3, verbose=i2c_setting_verbose):
                    logger.warning(f"Failed to set Top settings OffLR for ASIC {_asic} for run")
        
        # * --- Save the data -----------------------------------------------------
        data_file.close()

finally:
    socket_udp.close()
    logger.info("Socket closed")

true_count = sum(measurement_good_array)  # 'True' is counted as 1, 'False' as 0
total_count = len(measurement_good_array)
true_percentage = (true_count / total_count) * 100

logger.info(f"Total count: {total_count}")
logger.info(f"True count: {true_count}")
logger.info(f"False count: {total_count - true_count}")
logger.info(f"Percentage of True values: {true_percentage:.2f}%")
import packetlib
import socket
import numpy as np
import time
import json
import os
import logging
import colorlog
import re
from icmplib import ping
from tqdm import tqdm

# * --- Set up script information -------------------------------------
script_id_str       = '107_GeneralConfig'
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

# ! --- Set up whether to use external config file --------------------
use_external_config = True

# * --- Set up external config file -----------------------------------
external_config_chn_wise_name_a0 = 'a0f0Channelwise.txt'
external_config_main_reg_name_a0 = 'a0f0MainReg.txt'

external_config_chn_wise_name_a1 = 'a1f0Channelwise.txt'
external_config_main_reg_name_a1 = 'a1f0MainReg.txt'

external_config_chn_wise_path_a0 = os.path.join('config', external_config_chn_wise_name_a0)
external_config_main_reg_path_a0 = os.path.join('config', external_config_main_reg_name_a0)
external_config_chn_wise_path_a1 = os.path.join('config', external_config_chn_wise_name_a1)
external_config_main_reg_path_a1 = os.path.join('config', external_config_main_reg_name_a1)

external_config_chn_wise_dict_a0 = {}
external_config_main_reg_dict_a0 = {}
external_config_chn_wise_dict_a1 = {}
external_config_main_reg_dict_a1 = {}
try:
    with open(external_config_chn_wise_path_a0, 'r') as f:
        for line in f:
            # remove \n at the end of the line
            line = line.strip()
            if not line.startswith('#'):
                # words are separated by three spaces
                words = re.split(r' {2,}', line) 
                info_str = words[0].strip()
                # all the following words are hex values with 0x prefix
                hex_values = [int(word, 16) for word in words[1:]]
                hex_values = bytearray(hex_values)

                external_config_chn_wise_dict_a0[info_str] = hex_values
except FileNotFoundError:
    logger.warning(f"External config file not found: {external_config_chn_wise_path_a0}")

# logger.debug(f"External config file for channel-wise settings: {external_config_chn_wise_dict_a0}")

try:
    with open(external_config_main_reg_path_a0, 'r') as f:
        for line in f:
            # remove \n at the end of the line
            line = line.strip()
            if not line.startswith('#'):
                # words are separated by three spaces
                words = re.split(r'\s+', line)
                info_str = words[0].strip()
                # all the following words are hex values with 0x prefix
                hex_values = [int(word, 16) for word in words[1:]]

                external_config_main_reg_dict_a0[info_str] = hex_values
except FileNotFoundError:
    logger.warning(f"External config file not found: {external_config_main_reg_path_a0}")

# logger.debug(f"External config file for main register settings: {external_config_main_reg_dict_a0}")

try:
    with open(external_config_chn_wise_path_a1, 'r') as f:
        for line in f:
            # remove \n at the end of the line
            line = line.strip()
            if not line.startswith('#'):
                # words are separated by three spaces
                words = re.split(r' {2,}', line) 
                info_str = words[0].strip()
                # all the following words are hex values with 0x prefix
                hex_values = [int(word, 16) for word in words[1:]]
                hex_values = bytearray(hex_values)

                external_config_chn_wise_dict_a1[info_str] = hex_values
except FileNotFoundError:
    logger.warning(f"External config file not found: {external_config_chn_wise_path_a1}")

# logger.debug(f"External config file for channel-wise settings: {external_config_chn_wise_dict_a1}")

try:
    with open(external_config_main_reg_path_a1, 'r') as f:
        for line in f:
            # remove \n at the end of the line
            line = line.strip()
            if not line.startswith('#'):
                # words are separated by three spaces
                words = re.split(r'\s+', line)
                info_str = words[0].strip()
                # all the following words are hex values with 0x prefix
                hex_values = [int(word, 16) for word in words[1:]]

                external_config_main_reg_dict_a1[info_str] = hex_values
except FileNotFoundError:
    logger.warning(f"External config file not found: {external_config_main_reg_path_a1}")

# logger.debug(f"External config file for main register settings: {external_config_main_reg_dict_a1}")

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
HV_on         = [0xA0, 0x00, 0x03, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
while len(HV_on) < 40:
    HV_on.append(0x00)

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
fpga_address        = 0x00

machine_gun_val             = 9
gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011

ex_trg_delay_value          = 0
ex_trg_deadtime_value       = 200

gen_pre_inverval_value      = 200
gen_nr_cycle                = 1
gen_interval_value          = 100

i2c_setting_verbose = False

if gen_nr_cycle*(1+machine_gun_val)*4 > 300:
    logger.warning("Too much packet requested")

try:

    # * --- Set up channel-wise registers -------------------------------------
    logger.info("Setting up channel-wise registers")
    if not use_external_config:
        for _chn in range(152):
            _asic_num   = _chn // 76
            _chn_num    = _chn % 76
            _half_num   = _chn_num // 38
            _sub_addr   =  packetlib.uni_chn_to_subblock_list[_chn_num]

            _chn_content = default_channel_wise.copy()
            _chn_content[3] = int(trim_dac_values[_chn]) << 2

            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, retry=3, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set ChannelWise settings for ASIC {_asic_num}")
    else:
        _retry = 3
        for _try in range(_retry):
            for _key, _value in external_config_chn_wise_dict_a0.items():
                # logger.info(f"Setting up channel-wise register {_key}")
                socket_udp.sendto(bytes(_value), (h2gcroc_ip, h2gcroc_port))
                time.sleep(0.02)
            for _key, _value in external_config_chn_wise_dict_a1.items():
                # logger.info(f"Setting up channel-wise register {_key}")
                socket_udp.sendto(bytes(_value), (h2gcroc_ip, h2gcroc_port))
                time.sleep(0.02)

    # * --- Set up digital registers ------------------------------------------
    logger.info("Setting up main registers")
    if not use_external_config:
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

    else:
        _retry = 3
        for _try in range(_retry):
            for _key, _value in external_config_main_reg_dict_a0.items():
                # logger.info(f"Setting up main register {_key}")
                socket_udp.sendto(bytes(_value), (h2gcroc_ip, h2gcroc_port))
                time.sleep(0.02)
            for _key, _value in external_config_main_reg_dict_a1.items():
                # logger.info(f"Setting up main register {_key}")
                socket_udp.sendto(bytes(_value), (h2gcroc_ip, h2gcroc_port))
                time.sleep(0.02)

    # * --- Set up HV ---------------------------------------------------------
    logger.info("Setting up HV")
    socket_udp.sendto(bytes(HV_on), (h2gcroc_ip, h2gcroc_port))

    if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=0, gen_pre_interval = gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=gen_fcmd_internal_injection,ext_trg_en=1, ext_trg_delay=ex_trg_delay_value, ext_trg_deadtime=ex_trg_deadtime_value, gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val,verbose=False):
        print('\033[33m' + "Warning: Generator parameters not match" + '\033[0m')

finally:
    logger.info("Closing the socket")
    socket_udp.close()
    
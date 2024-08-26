import packetlib
import socket
import numpy as np
import time
import json
import os
import logging
import colorlog
from icmplib import ping
import argparse
from tqdm import tqdm

import matplotlib.pyplot as plt

# * --- Set up script information -------------------------------------
script_id_str       = '604_SystemConfig'
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

# * --- Set up argument parser -----------------------------------------
parser = argparse.ArgumentParser(description='System Configuration')
parser.add_argument('--pedeA', type=str, help='Pedestal file for board A')
parser.add_argument('--pedeB', type=str, help='Pedestal file for board B')
parser.add_argument('--totA', type=str, help='ToT/ToA calibration file for board A')
parser.add_argument('--totB', type=str, help='ToT/ToA calibration file for board B')

args = parser.parse_args()

# * --- Set up output folder -------------------------------------------
output_folder = 'dump'

output_runtime_json_name = f'{script_id_str}_runtime' + time.strftime("_%Y%m%d_%H%M%S", time.localtime()) + '.json'
output_runtime_json_path = os.path.join(output_folder, output_runtime_json_name)

output_runtime_json = {}

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# * --- Set up UDP communication --------------------------------------
h2gcroc_ip_A    = "10.1.2.208"
h2gcroc_port_A  = 11000
h2gcroc_ip_B    = "10.1.2.209"
h2gcroc_port_B  = 11000

pc_ip           = "10.1.2.207"
pc_port         = 11000
timeout         = 3 # seconds

logger.info(f"Board A H2G IP: {h2gcroc_ip_A}")
logger.info(f"Board A H2G Port: {h2gcroc_port_A}")
logger.info(f"Board A PC IP: {pc_ip}")
logger.info(f"Board A PC Port: {pc_port}")

ping_result = ping(pc_ip, count=1)
if ping_result.is_alive:
    logger.info(f"PC IP {pc_ip} is reachable")
else:
    logger.critical(f"PC IP {pc_ip} is not reachable")
    logger.critical("Please check the network settings")
    exit()

socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_udp.bind((pc_ip, pc_port))
socket_udp.settimeout(timeout)

# * I2C register settings
# * ---------------------------------------------------------------------------
i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

top_reg_runLR = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
top_reg_offLR = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]

HV_on_A =  [0xA0, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
HV_off_A = [0xA0, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
HV_on_B =  [0xA0, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
HV_off_B = [0xA0, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

while len(HV_on_A) < 40:
    HV_on_A.append(0x00)
while len(HV_off_A) < 40:
    HV_off_A.append(0x00)
while len(HV_on_B) < 40:
    HV_on_B.append(0x00)
while len(HV_off_B) < 40:
    HV_off_B.append(0x00)

default_global_analog   = reg_settings.get_default_reg_content('registers_global_analog')
default_global_analog[8]  = 0xA0
default_global_analog[9]  = 0xCA
default_global_analog[10] = 0x42
default_global_analog[14] = 0x6F

default_channel_wise    = reg_settings.get_default_reg_content('registers_channel_wise')
default_channel_wise[14] = 0xC0 # Gain_conv<2> and sign_dac
# 0xC0 - default, 0xD4, 0xEA and 0xFF

default_reference_voltage = reg_settings.get_default_reg_content('registers_reference_voltage')
default_reference_voltage[10] = 0x07

default_digital_half = reg_settings.get_default_reg_content('registers_digital_half')
default_digital_half[4] = 0xC0
default_digital_half[25] = 0x02

# * Generator settings
# * ---------------------------------------------------------------------------
total_asic                  = 2

machine_gun_val             = 5

gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011

gen_pre_inverval_value      = 200
gen_nr_cycle                = 1
gen_interval_value          = 100

gen_ex_dead_time            = 0xFF
gen_ex_trg_delay            = 0
L1_offset                   = 4

phase_shift                 = 0

top_reg_offLR[7] = phase_shift
top_reg_runLR[7] = phase_shift

output_runtime_json["generator"] = {}
output_runtime_json["generator"]["machine_gun_val"] = machine_gun_val
output_runtime_json["generator"]["gen_fcmd_internal_injection"] = gen_fcmd_internal_injection
output_runtime_json["generator"]["gen_fcmd_L1A"] = gen_fcmd_L1A
output_runtime_json["generator"]["gen_pre_inverval_value"] = gen_pre_inverval_value
output_runtime_json["generator"]["gen_nr_cycle"] = gen_nr_cycle
output_runtime_json["generator"]["gen_interval_value"] = gen_interval_value

# * --- Find all calibration files -------------------------------------
pedeA = args.pedeA
pedeB = args.pedeB
totA  = args.totA
totB  = args.totB

pedestal_calib_file_prefix = "pede_calib_config"
pedestal_calib_folder = "dump"

tottoa_calib_file_prefix = "ToT_ToA_Calib"
tottoa_calib_folder = "dump"

if not pedeA:
    # * Find the latest pedestal file for board A
    pedeA_candidates = [f for f in os.listdir(pedestal_calib_folder) if f.startswith(pedestal_calib_file_prefix) and f.endswith(".json")]
    pedeA_candidates.sort(reverse=True)

    newset_pedeA_found = False
    if len(pedeA_candidates) > 0:
        for pedeA_candidate in pedeA_candidates:
            with open(os.path.join(pedestal_calib_folder, pedeA_candidate), 'r') as f:
                pedeA_json = json.load(f)
                if pedeA_json['udp']['h2gcroc_ip'] == h2gcroc_ip_A:
                    pedeA = os.path.join(pedestal_calib_folder, pedeA_candidate)
                    newset_pedeA_found = True
                    break
    if not newset_pedeA_found:
        logger.critical("No pedestal calibration file found for board A")
        exit()
    else:
        logger.info(f"Using pedestal calibration file for board A: {pedeA}")
else:
    pedeA = os.path.join(pedestal_calib_folder, pedeA)
    if not os.path.exists(pedeA):
        logger.critical(f"Pedestal calibration file for board A not found: {pedeA}")
        exit()

if not pedeB:
    # * Find the latest pedestal file for board B
    pedeB_candidates = [f for f in os.listdir(pedestal_calib_folder) if f.startswith(pedestal_calib_file_prefix) and f.endswith(".json")]
    pedeB_candidates.sort(reverse=True)

    newset_pedeB_found = False
    if len(pedeB_candidates) > 0:
        for pedeB_candidate in pedeB_candidates:
            with open(os.path.join(pedestal_calib_folder, pedeB_candidate), 'r') as f:
                pedeB_json = json.load(f)
                if pedeB_json['udp']['h2gcroc_ip'] == h2gcroc_ip_B:
                    pedeB = os.path.join(pedestal_calib_folder, pedeB_candidate)
                    newset_pedeB_found = True
                    break
    if not newset_pedeB_found:
        logger.critical("No pedestal calibration file found for board B")
        exit()
    else:
        logger.info(f"Using pedestal calibration file for board B: {pedeB}")
else:
    pedeB = os.path.join(pedestal_calib_folder, pedeB)
    if not os.path.exists(pedeB):
        logger.critical(f"Pedestal calibration file for board B not found: {pedeB}")
        exit()

if not totA:
    # * Find the latest ToT/ToA calibration file for board A
    totA_candidates = [f for f in os.listdir(tottoa_calib_folder) if f.startswith(tottoa_calib_file_prefix) and f.endswith(".json")]
    totA_candidates.sort(reverse=True)

    newset_totA_found = False
    if len(totA_candidates) > 0:
        for totA_candidate in totA_candidates:
            with open(os.path.join(tottoa_calib_folder, totA_candidate), 'r') as f:
                totA_json = json.load(f)
                if totA_json['udp']['h2gcroc_ip'] == h2gcroc_ip_A:
                    totA = os.path.join(tottoa_calib_folder, totA_candidate)
                    newset_totA_found = True
                    break
    if not newset_totA_found:
        logger.critical("No ToT/ToA calibration file found for board A")
        exit()
    else:
        logger.info(f"Using ToT/ToA calibration file for board A: {totA}")
else:
    totA = os.path.join(tottoa_calib_folder, totA)
    if not os.path.exists(totA):
        logger.critical(f"ToT/ToA calibration file for board A not found: {totA}")
        exit()

if not totB:
    # * Find the latest ToT/ToA calibration file for board B
    totB_candidates = [f for f in os.listdir(tottoa_calib_folder) if f.startswith(tottoa_calib_file_prefix) and f.endswith(".json")]
    totB_candidates.sort(reverse=True)

    newset_totB_found = False
    if len(totB_candidates) > 0:
        for totB_candidate in totB_candidates:
            with open(os.path.join(tottoa_calib_folder, totB_candidate), 'r') as f:
                totB_json = json.load(f)
                if totB_json['udp']['h2gcroc_ip'] == h2gcroc_ip_B:
                    totB = os.path.join(tottoa_calib_folder, totB_candidate)
                    newset_totB_found = True
                    break
    if not newset_totB_found:
        logger.critical("No ToT/ToA calibration file found for board B")
        exit()
    else:
        logger.info(f"Using ToT/ToA calibration file for board B: {totB}")
else:
    totB = os.path.join(tottoa_calib_folder, totB)
    if not os.path.exists(totB):
        logger.critical(f"ToT/ToA calibration file for board B not found: {totB}")
        exit()

# * --- Load calibration files -----------------------------------------
trim_dac_values_A   = []
trim_dac_values_B   = []
inputdac_values_A   = []
inputdac_values_B   = []
noinv_vref_values_A = []
noinv_vref_values_B = []
inv_vref_values_A   = []
inv_vref_values_B   = []
dead_channels_A     = []
dead_channels_B     = []
not_used_channels_A = []
not_used_channels_B = []

try:
    with open(pedeA, 'r') as f:
        pedeA_json = json.load(f)
        trim_dac_values_A   = pedeA_json['chn_trim_settings']
        inputdac_values_A   = pedeA_json['chn_inputdac_settings']
        noinv_vref_values_A = pedeA_json['noinv_vref_list']
        inv_vref_values_A   = pedeA_json['inv_vref_list']
        dead_channels_A     = pedeA_json['dead_channels']
        not_used_channels_A = pedeA_json['channel_not_used']
except Exception as e:
    logger.error(f"Error loading pedestal calibration file for board A: {e}")
    exit()

try:
    with open(pedeB, 'r') as f:
        pedeB_json = json.load(f)
        trim_dac_values_B   = pedeB_json['chn_trim_settings']
        inputdac_values_B   = pedeB_json['chn_inputdac_settings']
        noinv_vref_values_B = pedeB_json['noinv_vref_list']
        inv_vref_values_B   = pedeB_json['inv_vref_list']
        dead_channels_B     = pedeB_json['dead_channels']
        not_used_channels_B = pedeB_json['channel_not_used']
except Exception as e:
    logger.error(f"Error loading pedestal calibration file for board B: {e}")
    exit()

tot_half_threshold_A = []
tot_chn_trim_A       = []
toa_half_threshold_A = []
toa_chn_trim_A       = []

tot_half_threshold_B = []
tot_chn_trim_B       = []
toa_half_threshold_B = []
toa_chn_trim_B       = []

try:
    with open(totA, 'r') as f:
        totA_json = json.load(f)
        tot_half_threshold_A = totA_json['ToT_Half_Threshold']
        tot_chn_trim_A       = totA_json['ToT_Chn_Trim']
        toa_half_threshold_A = totA_json['ToA_Half_Threshold']
        toa_chn_trim_A       = totA_json['ToA_Chn_Trim']
except Exception as e:
    logger.error(f"Error loading ToT/ToA calibration file for board A: {e}")
    exit()

try:
    with open(totB, 'r') as f:
        totB_json = json.load(f)
        tot_half_threshold_B = totB_json['ToT_Half_Threshold']
        tot_chn_trim_B       = totB_json['ToT_Chn_Trim']
        toa_half_threshold_B = totB_json['ToA_Half_Threshold']
        toa_chn_trim_B       = totB_json['ToA_Chn_Trim']
except Exception as e:
    logger.error(f"Error loading ToT/ToA calibration file for board B: {e}")
    exit()

output_runtime_json['input'] = {}
output_runtime_json['input']['pedeA'] = pedeA
output_runtime_json['input']['pedeB'] = pedeB
output_runtime_json['input']['totA'] = totA
output_runtime_json['input']['totB'] = totB

try:
    # * --- Set up channel-wise settings -----------------------------------
    logger.info("Setting up channel-wise settings for board A")
    fpga_address = 0x00
    for _chn in range(152):
        if _chn in dead_channels_A or _chn in not_used_channels_A:
            continue
        _asic_num = _chn // 76
        _chn_num  = _chn % 76
        _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

        _chn_wise = default_channel_wise.copy()
        _chn_wise[0] = inputdac_values_A[_chn] & 0x3F
        _chn_wise[1] = (toa_chn_trim_A[_chn] & 0x3F) << 2  
        _chn_wise[2] = (tot_chn_trim_A[_chn] & 0x3F) << 2
        _chn_wise[3] = (trim_dac_values_A[_chn] & 0x3F) << 2

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
            logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num} in board A, channel {_chn}")

    logger.info("Setting up channel-wise settings for board B")
    fpga_address = 0x01
    for _chn in range(152):
        if _chn in dead_channels_B or _chn in not_used_channels_B:
            continue
        _asic_num = _chn // 76
        _chn_num  = _chn % 76
        _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

        _chn_wise = default_channel_wise.copy()
        _chn_wise[0] = inputdac_values_B[_chn] & 0x3F
        _chn_wise[1] = (toa_chn_trim_B[_chn] & 0x3F) << 2  
        _chn_wise[2] = (tot_chn_trim_B[_chn] & 0x3F) << 2
        _chn_wise[3] = (trim_dac_values_B[_chn] & 0x3F) << 2

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
            logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num} in board B, channel {_chn}")

    # * --- Set up global analog settings ----------------------------------
    logger.info("Setting up global analog settings for board A")
    for _asic in range(total_asic):
        _global_analog = default_global_analog.copy()
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic, fpga_addr=0x00, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=_global_analog, retry=5, verbose=False):
            logger.warning(f"Failed to set Global Analog 0 settings for ASIC {_asic} in board A")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic, fpga_addr=0x00, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=_global_analog, retry=5, verbose=False):
            logger.warning(f"Failed to set Global Analog 1 settings for ASIC {_asic} in board A")

    logger.info("Setting up global analog settings for board B")
    for _asic in range(total_asic):
        _global_analog = default_global_analog.copy()
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic, fpga_addr=0x01, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=_global_analog, retry=5, verbose=False):
            logger.warning(f"Failed to set Global Analog 0 settings for ASIC {_asic} in board B")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic, fpga_addr=0x01, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=_global_analog, retry=5, verbose=False):
            logger.warning(f"Failed to set Global Analog 1 settings for ASIC {_asic} in board B")

    # * --- Set up digital registers ---------------------------------------
    logger.info("Setting up digital registers for board A")
    for _asic in range(total_asic):
        _digital_half = default_digital_half.copy()
        _digital_half[15] = L1_offset
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic, fpga_addr=0x00, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_half, retry=5, verbose=False):
            logger.warning(f"Failed to set Digital Half 0 settings for ASIC {_asic} in board A")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic, fpga_addr=0x00, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=_digital_half, retry=5, verbose=False):
            logger.warning(f"Failed to set Digital Half 1 settings for ASIC {_asic} in board A")

    logger.info("Setting up digital registers for board B")
    for _asic in range(total_asic):
        _digital_half = default_digital_half.copy()
        _digital_half[15] = L1_offset
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic, fpga_addr=0x01, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_half, retry=5, verbose=False):
            logger.warning(f"Failed to set Digital Half 0 settings for ASIC {_asic} in board B")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic, fpga_addr=0x01, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=_digital_half, retry=5, verbose=False):
            logger.warning(f"Failed to set Digital Half 1 settings for ASIC {_asic} in board B")

    # * --- Set up reference voltage settings -------------------------------
    logger.info("Setting up reference voltage settings for board A")
    fpga_address = 0x00
    for _asic in range(total_asic):
        _ref_content_half0  = default_reference_voltage.copy()
        _ref_content_half1  = default_reference_voltage.copy()
        _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_values_A[_asic_num*2] & 0x03) << 2) | (noinv_vref_values_A[_asic_num*2] & 0x03)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_values_A[_asic_num*2+1] & 0x03) << 2) | (noinv_vref_values_A[_asic_num*2+1] & 0x03)
        _ref_content_half0[1] = (_ref_content_half0[1] & 0x0F) | ((toa_half_threshold_A[_asic_num*2] & 0x03) << 4) | ((tot_half_threshold_A[_asic_num*2] & 0x03) << 2)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0x0F) | ((toa_half_threshold_A[_asic_num*2+1] & 0x03) << 4) | ((tot_half_threshold_A[_asic_num*2+1] & 0x03) << 2)
        _ref_content_half0[2] = tot_half_threshold_A[_asic_num*2] >> 2
        _ref_content_half1[2] = tot_half_threshold_A[_asic_num*2+1] >> 2
        _ref_content_half0[3] = toa_half_threshold_A[_asic_num*2] >> 2
        _ref_content_half1[3] = toa_half_threshold_A[_asic_num*2+1] >> 2
        _ref_content_half0[4] = inv_vref_values_A[_asic_num*2] >> 2
        _ref_content_half1[4] = inv_vref_values_A[_asic_num*2+1] >> 2
        _ref_content_half0[5] = noinv_vref_values_A[_asic_num*2] >> 2
        _ref_content_half1[5] = noinv_vref_values_A[_asic_num*2+1] >> 2
        _ref_content_half0[6] = 0x00 # 12-bit internal dac
        _ref_content_half1[6] = 0x00 # 12-bit internal dac
        _ref_content_half0[7] = 0x00 # 12-bit internal dac
        _ref_content_half1[7] = 0x00 # 12-bit internal dac

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, retry=3, verbose=False):
            logger.warning(f"Failed to set Reference Voltage 0 settings for ASIC {_asic_num} in board A")
        
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, retry=3, verbose=False):
            logger.warning(f"Failed to set Reference Voltage 1 settings for ASIC {_asic_num} in board A")

    logger.info("Setting up reference voltage settings for board B")
    fpga_address = 0x01

    for _asic in range(total_asic):
        _ref_content_half0  = default_reference_voltage.copy()
        _ref_content_half1  = default_reference_voltage.copy()
        _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_values_B[_asic_num*2] & 0x03) << 2) | (noinv_vref_values_B[_asic_num*2] & 0x03)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_values_B[_asic_num*2+1] & 0x03) << 2) | (noinv_vref_values_B[_asic_num*2+1] & 0x03)
        _ref_content_half0[1] = (_ref_content_half0[1] & 0x0F) | ((toa_half_threshold_B[_asic_num*2] & 0x03) << 4) | ((tot_half_threshold_B[_asic_num*2] & 0x03) << 2)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0x0F) | ((toa_half_threshold_B[_asic_num*2+1] & 0x03) << 4) | ((tot_half_threshold_B[_asic_num*2+1] & 0x03) << 2)
        _ref_content_half0[2] = tot_half_threshold_B[_asic_num*2] >> 2
        _ref_content_half1[2] = tot_half_threshold_B[_asic_num*2+1] >> 2
        _ref_content_half0[3] = toa_half_threshold_B[_asic_num*2] >> 2
        _ref_content_half1[3] = toa_half_threshold_B[_asic_num*2+1] >> 2
        _ref_content_half0[4] = inv_vref_values_B[_asic_num*2] >> 2
        _ref_content_half1[4] = inv_vref_values_B[_asic_num*2+1] >> 2
        _ref_content_half0[5] = noinv_vref_values_B[_asic_num*2] >> 2
        _ref_content_half1[5] = noinv_vref_values_B[_asic_num*2+1] >> 2
        _ref_content_half0[6] = 0x00 # 12-bit internal dac
        _ref_content_half1[6] = 0x00 # 12-bit internal dac
        _ref_content_half0[7] = 0x00 # 12-bit internal dac
        _ref_content_half1[7] = 0x00 # 12-bit internal dac

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, retry=3, verbose=False):
            logger.warning(f"Failed to set Reference Voltage 0 settings for ASIC {_asic_num} in board B")

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, retry=3, verbose=False):
            logger.warning(f"Failed to set Reference Voltage 1 settings for ASIC {_asic_num} in board B")

    # * --- Set up Generator settings ---------------------------------------
    logger.info("Setting up Generator settings for board A")
    fpga_address = 0x00
    if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, 0, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=0, gen_pre_interval = gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=gen_fcmd_internal_injection,ext_trg_en=1, ext_trg_delay=gen_ex_trg_delay, ext_trg_deadtime=gen_ex_dead_time, gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val,verbose=False):
        logger.warning(f"Failed to set up the generator settings for board A")

    logger.info("Setting up Generator settings for board B")
    fpga_address = 0x01
    if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, 0, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=0, gen_pre_interval = gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=gen_fcmd_internal_injection,ext_trg_en=1, ext_trg_delay=gen_ex_trg_delay, ext_trg_deadtime=255, gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val,verbose=False):
        logger.warning(f"Failed to set up the generator settings for board B")

    # * --- Set up HV settings ---------------------------------------------
    logger.info("Setting up HV settings for board A")
    socket_udp.sendto(bytes(HV_on_A), (h2gcroc_ip_A, h2gcroc_port_A))
    time.sleep(0.5)
    logger.info("Setting up HV settings for board B")
    socket_udp.sendto(bytes(HV_on_B), (h2gcroc_ip_B, h2gcroc_port_B))
    time.sleep(0.5)

finally:
    socket_udp.close()


# * --- Save runtime settings -------------------------------------------
output_runtime_json["i2c"] = {}
output_runtime_json["i2c"]["top_reg_runLR"] = top_reg_runLR
output_runtime_json["i2c"]["top_reg_offLR"] = top_reg_offLR

with open(output_runtime_json_path, 'w') as f:
    json.dump(output_runtime_json, f, indent=4)

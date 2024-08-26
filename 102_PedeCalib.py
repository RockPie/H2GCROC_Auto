import packetlib
import socket
import numpy as np
import time
import json
import os
import logging
import colorlog
import matplotlib.pyplot as plt

from icmplib import ping
from tqdm import tqdm

# * --- Set up script information -------------------------------------
script_id_str       = '102_PedeCalib'
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
output_config_json = {}
output_pedecalib_json = {}

output_pedecalib_json_name = f'pede_calib_config_{time.strftime("%Y%m%d_%H%M%S")}.json'

output_dump_folder = os.path.join(output_dump_path, output_folder_name)
output_config_path = os.path.join(output_dump_path, output_config_json_name)
output_pedecalib_path = os.path.join(output_dump_path, output_pedecalib_json_name)

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
socket_udp.settimeout(timeout)

# * I2C register settings
# * ---------------------------------------------------------------------------
i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

top_reg_runLR = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x05,0x00]
top_reg_offLR = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x05,0x00]

default_global_analog   = reg_settings.get_default_reg_content('registers_global_analog')
default_global_analog[8]  = 0xA0
default_global_analog[9]  = 0xCA
default_global_analog[10] = 0x42
default_global_analog[14] = 0x6F

default_channel_wise      = reg_settings.get_default_reg_content('registers_channel_wise')
default_channel_wise[14]  = 0x80

default_reference_voltage = reg_settings.get_default_reg_content('registers_reference_voltage')

output_config_json["i2c"] = {}
output_config_json["i2c"]["top_reg_runLR"] = top_reg_runLR
output_config_json["i2c"]["top_reg_offLR"] = top_reg_offLR

# * --- Set running parameters ------------------------------------------------
total_asic          = 2
fpga_address        = int(h2gcroc_ip.split('.')[-1]) - 208
fragment_life       = 3
channel_not_used    = [0, 19, 38, 57, 76, 95, 114, 133] # here are the CM channels
dead_channels       = []

gen_nr_cycle        = 10
gen_interval_value  = 40

gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011

scan0_target = 100
scan1_target = 100
scan2_target = 100
scan3_target = scan2_target

chn_trim_scan_step_corse = 1
chn_trim_scan_step_fine  = 2
ref_inv_scan_step_corse  = 50
ref_inv_scan_step_fine   = 20

dead_chn_std_threshold = 5
dead_chn_mean_threshold = 80 # ! it is a temporary approach

# half pedestal default values:
initial_inv_vref_list   = [400,400,400,400]
initial_noinv_vref_list = [800,800,800,800]

i2c_setting_verbose = False

output_pedecalib_json['running_parameters'] = {
    'total_asic': total_asic,
    'fpga_address': fpga_address,
    'fragment_life': fragment_life,
    'channel_not_used': channel_not_used,
    'dead_channels': dead_channels,
    'gen_nr_cycle': gen_nr_cycle,
    'gen_interval_value': gen_interval_value,
    'gen_fcmd_internal_injection': gen_fcmd_internal_injection,
    'gen_fcmd_L1A': gen_fcmd_L1A,
    'scan0_target': scan0_target,
    'scan1_target': scan1_target,
    'scan2_target': scan2_target,
    'scan3_target': scan3_target,
    'chn_trim_scan_step_corse': chn_trim_scan_step_corse,
    'chn_trim_scan_step_fine': chn_trim_scan_step_fine,
    'ref_inv_scan_step_corse': ref_inv_scan_step_corse,
    'ref_inv_scan_step_fine': ref_inv_scan_step_fine,
    'dead_chn_std_threshold': dead_chn_std_threshold,
    'dead_chn_mean_threshold': dead_chn_mean_threshold,
    'initial_inv_vref_list': initial_inv_vref_list,
    'initial_noinv_vref_list': initial_noinv_vref_list,
    'i2c_setting_verbose': i2c_setting_verbose
}

final_ref_inv_list      = []
final_ref_noinv_list    = []
final_chn_trim_list     = []

try:
# * --- Set up the generator --------------------------------------------------
    if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0x00, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=0, gen_pre_interval = 10, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=75, gen_fcmd=75,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=0x00, verbose=False):
        logger.warning(f"Failed to set up the generator")
# * --- Set up the I2C settings -----------------------------------------------
    for _asic in range(total_asic):

        # * --- Global_Analog_0 & Global_Analog_1 ---
        _global_analog = default_global_analog.copy()

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=_global_analog, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Global_Analog_0 settings for ASIC {_asic}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=_global_analog, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Global_Analog_1 settings for ASIC {_asic}")
        
        # * --- Reference Voltage Half 0 & Half 1 ---
        _ref_voltage_half0 = default_reference_voltage.copy()
        _ref_voltage_half1 = default_reference_voltage.copy()

        _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((initial_inv_vref_list[_asic*2] & 0x03) << 2) | (initial_noinv_vref_list[_asic*2] & 0x03)
        _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((initial_inv_vref_list[_asic*2+1] & 0x03) << 2) | (initial_noinv_vref_list[_asic*2+1] & 0x03)

        _ref_voltage_half0[4] = initial_inv_vref_list[_asic*2] >> 2
        _ref_voltage_half1[4] = initial_inv_vref_list[_asic*2 + 1] >> 2
        _ref_voltage_half0[5] = initial_noinv_vref_list[_asic*2] >> 2
        _ref_voltage_half1[5] = initial_noinv_vref_list[_asic*2 + 1] >> 2

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

    scan0_inv_ref = initial_inv_vref_list.copy()
    scan0_noinv_ref = initial_noinv_vref_list.copy()

    # ! --- Scan 0 for reference voltage correlation ---
    progress_bar_scan_0 = tqdm(range(0, 1024, ref_inv_scan_step_corse))
    scan0_res_global_means = []
    scan0_res_global_errs  = []
    for _inv in progress_bar_scan_0:
        progress_bar_scan_0.set_description(f"Inv Ref " + "{:04d}".format(_inv))
        for _asic in range(total_asic):
            _ref_voltage_half0 = default_reference_voltage.copy()
            _ref_voltage_half1 = default_reference_voltage.copy()

            _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((_inv & 0x03) << 2) | (initial_noinv_vref_list[_asic*2] & 0x03)
            _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((_inv & 0x03) << 2) | (initial_noinv_vref_list[_asic*2+1] & 0x03)

            _ref_voltage_half0[4] = _inv >> 2
            _ref_voltage_half1[4] = _inv >> 2
            _ref_voltage_half0[5] = initial_noinv_vref_list[_asic*2] >> 2
            _ref_voltage_half1[5] = initial_noinv_vref_list[_asic*2 + 1] >> 2

            # _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((initial_inv_vref_list[_asic*2] & 0x03) << 2) | (_inv  & 0x03)
            # _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((initial_inv_vref_list[_asic*2+1] & 0x03) << 2) | (_inv  & 0x03)

            # _ref_voltage_half0[4] = initial_inv_vref_list[_asic*2] >> 2
            # _ref_voltage_half1[4] = initial_inv_vref_list[_asic*2 + 1] >> 2
            # _ref_voltage_half0[5] = _inv  >> 2
            # _ref_voltage_half1[5] = _inv  >> 2
        
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=5, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")

            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=5, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

        # ! --- Data reading sequence ---
        for _asic in range(2):
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
                logger.warning(f"Failed to turn on LR for ASIC {_asic}")

        packetlib.clean_socket(socket_udp)

        if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
            logger.warning("Failed to start the generator")

        extracted_payloads_pool = []
        event_fragment_pool     = []
        fragment_life_dict      = {}

        expected_event_num = gen_nr_cycle

        current_half_packet_num = 0
        current_event_num = 0

        all_chn_value_0_array = np.zeros((expected_event_num, 152))
        all_chn_value_1_array = np.zeros((expected_event_num, 152))
        all_chn_value_2_array = np.zeros((expected_event_num, 152))
        hamming_code_array    = np.zeros((expected_event_num, 12))

        while True:
            try:
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
                    else:
                        logger.warning("Warning: Event fragment is not good")
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
                            else:
                                fragment_life_dict[timestamp0] += 1
                        else:
                            fragment_life_dict[timestamp0] = 1
                        i += 1
                for index in sorted(indices_to_delete, reverse=True):
                    del event_fragment_pool[index]

                if current_event_num == expected_event_num:
                    break;
                            
            except Exception as e:
                logger.warning("Exception in receiving data")
                logger.warning(e)
                logger.warning('Packet received: ' + str(current_half_packet_num))
                logger.warning('left fragments:' + str(len(event_fragment_pool)))
                logger.warning("current event num:" + str(current_event_num))
                measurement_good_flag = False
                break

        if not np.all(hamming_code_array == 0):
            logger.warning("Hamming code error detected!")
            measurement_good_flag = False

        if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
            logger.warning("Failed to stop the generator")

        for _asic in range(2):
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
                logger.warning(f"Failed to turn off LR for ASIC {_asic}")

        _val0_mean_list = []
        _val0_err_list  = []
        for _chn in range(152):
            _candidate_values = []
            for _event in range(expected_event_num):
                if np.all(hamming_code_array[_event] == 0):
                    _candidate_values.append(all_chn_value_0_array[_event][_chn])
            if len(_candidate_values) > 0:
                _val0_mean_list.append(np.mean(_candidate_values))
                _val0_err_list.append(np.std(_candidate_values))
            else:
                logger.warning(f"Channel {_chn} has no valid data")
                _val0_mean_list.append(0)
                _val0_err_list.append(0)
        
        _mean_half0 = np.mean(_val0_mean_list[0:38])
        _mean_half1 = np.mean(_val0_mean_list[38:76])
        _mean_half2 = np.mean(_val0_mean_list[76:114])
        _mean_half3 = np.mean(_val0_mean_list[114:152])

        _std_half0 = np.std(_val0_mean_list[0:38])
        _std_half1 = np.std(_val0_mean_list[38:76])
        _std_half2 = np.std(_val0_mean_list[76:114])
        _std_half3 = np.std(_val0_mean_list[114:152])

        scan0_res_global_means.append([_mean_half0, _mean_half1, _mean_half2, _mean_half3])
        scan0_res_global_errs.append([_std_half0, _std_half1, _std_half2, _std_half3])

    scan0_inv_ref = initial_inv_vref_list.copy()
    scan0_noinv_ref = initial_noinv_vref_list.copy()

    # find the best reference voltage by the closest mean value to the target
    for _half in range(4):
        _best_mean = 9999
        _best_index = 0
        for _index in range(len(scan0_res_global_means)):
            _mean_diff = abs(scan0_res_global_means[_index][_half] - scan0_target)
            if _mean_diff < _best_mean:
                _best_mean = _mean_diff
                _best_index = _index
        scan0_inv_ref[_half] = list(range(0, 1024, ref_inv_scan_step_corse))[_best_index]
        # scan0_noinv_ref[_half] = list(range(0, 1024, ref_inv_scan_step_corse))[_best_index]

    logger.info(f"Scan 0 settings: Inv Ref: {scan0_inv_ref}, NoInv Ref: {scan0_noinv_ref}")

    for _asic in range(total_asic):
        _ref_voltage_half0 = default_reference_voltage.copy()
        _ref_voltage_half1 = default_reference_voltage.copy()

        _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((scan0_inv_ref[_asic*2] & 0x03) << 2) | (scan0_noinv_ref[_asic*2] & 0x03)
        _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((scan0_inv_ref[_asic*2+1] & 0x03) << 2) | (scan0_noinv_ref[_asic*2+1] & 0x03)

        _ref_voltage_half0[4] = scan0_inv_ref[_asic*2] >> 2
        _ref_voltage_half1[4] = scan0_inv_ref[_asic*2 + 1] >> 2
        _ref_voltage_half0[5] = scan0_noinv_ref[_asic*2] >> 2
        _ref_voltage_half1[5] = scan0_noinv_ref[_asic*2 + 1] >> 2

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")
        
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

    # ! --- Scan 1 for channel trim correlation ---
    progress_bar_scan_1 = tqdm(range(0, 20, chn_trim_scan_step_corse))
    scan1_res_chn_means = []
    scan1_res_chn_errs  = []
    for _trim in progress_bar_scan_1:
        progress_bar_scan_1.set_description(f"Chn Trim " + "{:02d}".format(_trim))
    #     _chn_wise = default_channel_wise.copy()
    #     _chn_wise[3] = (0x1F << 2) & 0xFC  # trim inv
    #     _chn_wise[0] = _trim  # input dac

    #     for _asic in range(total_asic):
    #         packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=_chn_wise, retry=3, verbose=i2c_setting_verbose)

    #         packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=_chn_wise, retry=3, verbose=i2c_setting_verbose)

        for _chn in range(152):
            _asic_num = _chn // 76
            _chn_num = _chn % 76
            _half_num = _chn_num // 38
            _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

            _chn_wise = default_channel_wise.copy()
            _chn_wise[3] = (0x1F << 2) & 0xFC  # trim inv
            if _chn in [133, 134, 135, 136, 137]:
                _chn_wise[0] = _trim  # input dac

            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num}")
        
        # packetlib.read_save_all_i2c(f"scan1_{_trim}.txt", socket_udp, h2gcroc_ip, h2gcroc_port, 2,  fpga_address)

        # ! --- Data reading sequence ---
        for _asic in range(2):
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
                logger.warning(f"Failed to turn on LR for ASIC {_asic}")

        packetlib.clean_socket(socket_udp)

        if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
            logger.warning("Failed to start the generator")

        extracted_payloads_pool = []
        event_fragment_pool     = []
        fragment_life_dict      = {}

        expected_event_num = gen_nr_cycle

        current_half_packet_num = 0
        current_event_num = 0

        all_chn_value_0_array = np.zeros((expected_event_num, 152))
        all_chn_value_1_array = np.zeros((expected_event_num, 152))
        all_chn_value_2_array = np.zeros((expected_event_num, 152))
        hamming_code_array    = np.zeros((expected_event_num, 12))

        while True:
            try:
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
                    else:
                        logger.warning("Warning: Event fragment is not good")
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
                            else:
                                fragment_life_dict[timestamp0] += 1
                        else:
                            fragment_life_dict[timestamp0] = 1
                        i += 1
                for index in sorted(indices_to_delete, reverse=True):
                    del event_fragment_pool[index]

                if current_event_num == expected_event_num:
                    break;
                            
            except Exception as e:
                logger.warning("Exception in receiving data")
                logger.warning(e)
                logger.warning('Packet received: ' + str(current_half_packet_num))
                logger.warning('left fragments:' + str(len(event_fragment_pool)))
                logger.warning("current event num:" + str(current_event_num))
                measurement_good_flag = False
                break

        if not np.all(hamming_code_array == 0):
            logger.warning("Hamming code error detected!")
            measurement_good_flag = False

        if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
            logger.warning("Failed to stop the generator")

        for _asic in range(2):
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
                logger.warning(f"Failed to turn off LR for ASIC {_asic}")

        _val0_mean_list = []
        _val0_err_list  = []
        for _chn in range(152):
            _candidate_values = []
            for _event in range(expected_event_num):
                if np.all(hamming_code_array[_event] == 0):
                    _candidate_values.append(all_chn_value_0_array[_event][_chn])
            if len(_candidate_values) > 0:
                _val0_mean_list.append(np.mean(_candidate_values))
                _val0_err_list.append(np.std(_candidate_values))
            else:
                logger.warning(f"Channel {_chn} has no valid data")
                _val0_mean_list.append(0)
                _val0_err_list.append(0)
                    
        scan1_res_chn_means.append(_val0_mean_list)
        scan1_res_chn_errs.append(_val0_err_list)
        # logger.debug("current res length:" + str(len(scan1_res_chn_means)))

    # find potential bad channels from std  
    std_list = []
    for _chn in range(152):
        _mean_list = []
        for _index in range(len(scan1_res_chn_means)):
            _mean_list.append(scan1_res_chn_means[_index][_chn])
        _std = np.std(_mean_list)
        std_list.append(_std)
        if _std < dead_chn_std_threshold and _chn not in channel_not_used:
            dead_channels.append(_chn)
    if len(dead_channels) > 0:
        logger.warning(f"Potential dead channels: {dead_channels}")

    # draw the std distribution
    fig_std, ax_std = plt.subplots(1, 1, figsize=(10, 6))
    ax_std.hist(std_list, bins=40, range=(0, max(std_list)))
    ax_std.set_xlabel('Standard Deviation')
    ax_std.set_ylabel('Counts')
    ax_std.set_title('Standard Deviation Distribution')
    plt.savefig(os.path.join(output_dump_folder, 'StdDistribution.png'))

    

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    for _chn in range(130, 152):
        _chn_means = []
        _chn_errs  = []
        for _index in range(len(scan1_res_chn_means)):
            _chn_means.append(scan1_res_chn_means[_index][_chn])
            _chn_errs.append(scan1_res_chn_errs[_index][_chn])
        ax.errorbar(range(0, 20, chn_trim_scan_step_corse), _chn_means, yerr=_chn_errs, label=f'Channel {_chn}')
    ax.set_xlabel('Channel Trim Value')
    ax.set_ylabel('Mean Value')
    ax.set_title('Channel Trim Scan')
    ax.legend()
    plt.savefig(os.path.join(output_dump_folder, 'ChannelTrimScan.png'))

    # find mean of mean values for each channel
    mean_mean_sum = [0,0,0,0]
    mean_mean_cnt = [0,0,0,0]
    for _chn in range(152):
        if _chn in channel_not_used or _chn in dead_channels:
            continue
        for _index in range(len(scan1_res_chn_means)):
            mean_mean_sum[_chn//38] += scan1_res_chn_means[_index][_chn]
            mean_mean_cnt[_chn//38] += 1
    for _half in range(4):
        if mean_mean_cnt[_half] == 0:
            continue
        mean_mean_sum[_half] /= mean_mean_cnt[_half]
    logger.info(f"Mean of mean values: {mean_mean_sum}")

    # find potential bad channels from the mean value
    _dist_list = []
    for _chn in range(152):
        if _chn in channel_not_used or _chn in dead_channels:
            continue
        _mean_list = []
        for _index in range(len(scan1_res_chn_means)):
            _mean_list.append(scan1_res_chn_means[_index][_chn])
        _mean = np.mean(_mean_list)
        _dist = abs(_mean - mean_mean_sum[_chn//38])
        _dist_list.append(_dist)
        if _dist > dead_chn_mean_threshold:
            dead_channels.append(_chn)

    if len(dead_channels) > 0:
        logger.warning(f"Potential dead channels: {dead_channels}")

    fig_dist, ax_dist = plt.subplots(1, 1, figsize=(10, 6))
    ax_dist.hist(_dist_list, bins=40, range=(0, max(_dist_list)))
    ax_dist.set_xlabel('Distance to Mean')
    ax_dist.set_ylabel('Counts')
    ax_dist.set_title('Distance to Mean Distribution')
    plt.savefig(os.path.join(output_dump_folder, 'DistDistribution.png'))

    # find max initial value for each half
    max_initial_value = [0, 0, 0, 0]
    for _chn in range(152):
        if _chn in channel_not_used or _chn in dead_channels:
            continue
        _scan_index = 0
        if scan1_res_chn_means[_scan_index][_chn] > max_initial_value[_chn//38]:
            max_initial_value[_chn//38] = scan1_res_chn_means[_scan_index][_chn]
    logger.info(f"Max initial values: {max_initial_value}")

    # See if the max initial value is higher than the final scan value
    risk_channels = []
    for _chn in range(152):
        if _chn in channel_not_used or _chn in dead_channels:
            continue
        _scan_index = len(scan1_res_chn_means) - 1
        if scan1_res_chn_means[_scan_index][_chn] < max_initial_value[_chn//38]:
            risk_channels.append(_chn)
    if len(risk_channels) > 0:
        logger.warning(f"Channels have largest value still lower than the initial max: {risk_channels}")

    # * Find the best channel trim value
    target_trim_output = max_initial_value.copy()
    chn_trim_values = np.zeros(152)
    for _chn in range(152):
        if _chn in channel_not_used or _chn in dead_channels:
            continue
        _best_mean = 9999
        _best_index = 0
        for _index in range(len(scan1_res_chn_means)):
            _mean_diff = abs(scan1_res_chn_means[_index][_chn] - target_trim_output[_chn//38])
            if _mean_diff < _best_mean:
                _best_mean = _mean_diff
                _best_index = _index
        chn_trim_values[_chn] = int(list(range(0, 20, chn_trim_scan_step_corse))[_best_index])
    logger.debug(f"Channel trim values: {chn_trim_values}")
    for _chn in range(152):
        _chn_wise = default_channel_wise.copy()
        _chn_wise[3] = int(chn_trim_values[_chn]) << 2
        # _chn_wise[0] = chn_trim_values[_chn] & 0x3F

        _asic = _chn // 76
        _half = (_chn % 76) // 38

        _sub_addr = packetlib.uni_chn_to_subblock_list[_chn % 76]

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set ChannelWise settings for ASIC {_asic}")

    # ! --- Data reading sequence ---
    for _asic in range(2):
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
            logger.warning(f"Failed to turn on LR for ASIC {_asic}")

    packetlib.clean_socket(socket_udp)

    if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
        logger.warning("Failed to start the generator")

    extracted_payloads_pool = []
    event_fragment_pool     = []

    expected_event_num = gen_nr_cycle

    current_half_packet_num = 0
    current_event_num = 0

    all_chn_value_0_array = np.zeros((expected_event_num, 152))
    all_chn_value_1_array = np.zeros((expected_event_num, 152))
    all_chn_value_2_array = np.zeros((expected_event_num, 152))
    hamming_code_array    = np.zeros((expected_event_num, 12))

    extracted_payloads_pool = []
    event_fragment_pool     = []
    fragment_life_dict      = {}

    expected_event_num = gen_nr_cycle

    current_half_packet_num = 0
    current_event_num = 0

    all_chn_value_0_array = np.zeros((expected_event_num, 152))
    all_chn_value_1_array = np.zeros((expected_event_num, 152))
    all_chn_value_2_array = np.zeros((expected_event_num, 152))
    hamming_code_array    = np.zeros((expected_event_num, 12))

    while True:
        try:
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
                else:
                    logger.warning("Warning: Event fragment is not good")
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
                        else:
                            fragment_life_dict[timestamp0] += 1
                    else:
                        fragment_life_dict[timestamp0] = 1
                    i += 1
            for index in sorted(indices_to_delete, reverse=True):
                del event_fragment_pool[index]
            if current_event_num == expected_event_num:
                break;
        except Exception as e:
            logger.warning("Exception in receiving data")
            logger.warning(e)
            logger.warning('Packet received: ' + str(current_half_packet_num))
            logger.warning('left fragments:' + str(len(event_fragment_pool)))
            logger.warning("current event num:" + str(current_event_num))
            measurement_good_flag = False
            break

    if not np.all(hamming_code_array == 0):
        logger.warning("Hamming code error detected!")
        measurement_good_flag = False
    if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0,daq_start_stop=0x00, verbose=False):
        logger.warning("Failed to stop the generator")
    for _asic in range(2):
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
            logger.warning(f"Failed to turn off LR for ASIC {_asic}")

    _val0_mean_list = []
    _val0_err_list  = []

    for _chn in range(152):
        _candidate_values = []
        for _event in range(expected_event_num):
            if np.all(hamming_code_array[_event] == 0):
                _candidate_values.append(all_chn_value_0_array[_event][_chn])
        if len(_candidate_values) > 0:
            _val0_mean_list.append(np.mean(_candidate_values))
            _val0_err_list.append(np.std(_candidate_values))
        else:
            logger.warning(f"Channel {_chn} has no valid data")
            _val0_mean_list.append(0)
            _val0_err_list.append(0)

    final_chn_trim_list = chn_trim_values.copy()
    final_ref_inv_list = scan0_inv_ref.copy()
    final_ref_noinv_list = scan0_noinv_ref.copy()

    # # ! --- Scan 2 for ref inv scan ---
    # progress_bar_scan_2 = tqdm(range(0, 1024, ref_inv_scan_step_fine))
    # scan2_res_global_means = []
    # scan2_res_global_errs  = []
    # for _inv in progress_bar_scan_2:
    #     progress_bar_scan_2.set_description(f"Inv Ref " + "{:04d}".format(_inv))
    #     for _asic in range(total_asic):
    #         _ref_voltage_half0 = default_reference_voltage.copy()
    #         _ref_voltage_half1 = default_reference_voltage.copy()

    #         _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((_inv & 0x03) << 2) | (initial_noinv_vref_list[_asic*2] & 0x03)
    #         _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((_inv & 0x03) << 2) | (initial_noinv_vref_list[_asic*2+1] & 0x03)

    #         _ref_voltage_half0[4] = _inv >> 2
    #         _ref_voltage_half1[4] = _inv >> 2
    #         _ref_voltage_half0[5] = initial_noinv_vref_list[_asic*2] >> 2
    #         _ref_voltage_half1[5] = initial_noinv_vref_list[_asic*2 + 1] >> 2

    #         if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=5, verbose=i2c_setting_verbose):
    #             logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")

    #         if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=5, verbose=i2c_setting_verbose):
    #             logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

    #     # ! --- Data reading sequence ---
    #     for _asic in range(2):
    #         if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
    #             logger.warning(f"Failed to turn on LR for ASIC {_asic}")

    #     packetlib.clean_socket(socket_udp)

    #     if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
    #         logger.warning("Failed to start the generator")

    #     extracted_payloads_pool = []
    #     event_fragment_pool     = []

    #     expected_event_num = gen_nr_cycle

    #     current_half_packet_num = 0
    #     current_event_num = 0

    #     all_chn_value_0_array = np.zeros((expected_event_num, 152))
    #     all_chn_value_1_array = np.zeros((expected_event_num, 152))
    #     all_chn_value_2_array = np.zeros((expected_event_num, 152))
    #     hamming_code_array    = np.zeros((expected_event_num, 12))

    #     while True:
    #         try:
    #             data_packet, rec_addr    = socket_udp.recvfrom(8192)
    #             # logger.debug("Packet received")
    #             extracted_payloads_pool += packetlib.extract_raw_payloads(data_packet)
    #             while len(extracted_payloads_pool) >= 5:
    #                 candidate_packet_lines = extracted_payloads_pool[:5]
    #                 is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
    #                 if is_packet_good:
    #                     event_fragment_pool.append(event_fragment)
    #                     current_half_packet_num += 1
    #                     extracted_payloads_pool = extracted_payloads_pool[5:]
    #                 else:
    #                     logger.warning("Warning: Event fragment is not good")
    #                     extracted_payloads_pool = extracted_payloads_pool[1:]
    #             indices_to_delete = set()
    #             if len(event_fragment_pool) >= 4:
    #                 event_fragment_pool = sorted(event_fragment_pool, key=lambda x: x[0][3:7])
    #             i = 0
    #             while i <= len(event_fragment_pool) - 4:
    #                 timestamp0 = event_fragment_pool[i][0][4] << 24 | event_fragment_pool[i][0][5] << 16 | event_fragment_pool[i][0][6] << 8 | event_fragment_pool[i][0][7]
    #                 timestamp1 = event_fragment_pool[i+1][0][4] << 24 | event_fragment_pool[i+1][0][5] << 16 | event_fragment_pool[i+1][0][6] << 8 | event_fragment_pool[i+1][0][7]
    #                 timestamp2 = event_fragment_pool[i+2][0][4] << 24 | event_fragment_pool[i+2][0][5] << 16 | event_fragment_pool[i+2][0][6] << 8 | event_fragment_pool[i+2][0][7]
    #                 timestamp3 = event_fragment_pool[i+3][0][4] << 24 | event_fragment_pool[i+3][0][5] << 16 | event_fragment_pool[i+3][0][6] << 8 | event_fragment_pool[i+3][0][7]
    #                 str_timestamp = f"{timestamp0:08X} {timestamp1:08X} {timestamp2:08X} {timestamp3:08X}"
    #                 if timestamp0 == timestamp1 and timestamp0 == timestamp2 and timestamp0 == timestamp3:
    #                     for _half in range(4):
    #                         extracted_data = packetlib.assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
    #                         extracted_values = packetlib.extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
    #                         uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
    #                         for j in range(len(extracted_values["_extracted_values"])):
    #                             all_chn_value_0_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
    #                             all_chn_value_1_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
    #                             all_chn_value_2_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
    #                         hamming_code_array[current_event_num][_half*3+0] =  packetlib.DaqH_get_H1(extracted_values["_DaqH"])
    #                         hamming_code_array[current_event_num][_half*3+1] =  packetlib.DaqH_get_H2(extracted_values["_DaqH"])
    #                         hamming_code_array[current_event_num][_half*3+2] =  packetlib.DaqH_get_H3(extracted_values["_DaqH"])
    #                     indices_to_delete.update([i, i+1, i+2, i+3])
    #                     current_event_num += 1
    #                     i += 4
    #                 else:
    #                     i += 1
    #                     # logger.debug(f"Timestamp: {str_timestamp}")
    #             for index in sorted(indices_to_delete, reverse=True):
    #                 del event_fragment_pool[index]
    #                 # logger.debug("current event num:" + str(current_event_num))
    #             if current_event_num == expected_event_num:
    #                 break;
                            
    #         except Exception as e:
    #             logger.warning("Exception in receiving data")
    #             logger.warning(e)
    #             logger.warning('Packet received: ' + str(current_half_packet_num))
    #             logger.warning('left fragments:' + str(len(event_fragment_pool)))
    #             logger.warning("current event num:" + str(current_event_num))
    #             measurement_good_flag = False
    #             break

    #     if not np.all(hamming_code_array == 0):
    #         logger.warning("Hamming code error detected!")
    #         measurement_good_flag = False

    #     if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
    #         logger.warning("Failed to stop the generator")

    #     for _asic in range(2):
    #         if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
    #             logger.warning(f"Failed to turn off LR for ASIC {_asic}")

    #     _val0_mean_list = []
    #     _val0_err_list  = []
    #     for _chn in range(152):
    #         _candidate_values = []
    #         for _event in range(expected_event_num):
    #             if np.all(hamming_code_array[_event] == 0):
    #                 _candidate_values.append(all_chn_value_0_array[_event][_chn])
    #         if len(_candidate_values) > 0:
    #             _val0_mean_list.append(np.mean(_candidate_values))
    #             _val0_err_list.append(np.std(_candidate_values))
    #         else:
    #             logger.warning(f"Channel {_chn} has no valid data")
    #             _val0_mean_list.append(0)
    #             _val0_err_list.append(0)
        
    #     _mean_half0 = np.mean(_val0_mean_list[0:38])
    #     _mean_half1 = np.mean(_val0_mean_list[38:76])
    #     _mean_half2 = np.mean(_val0_mean_list[76:114])
    #     _mean_half3 = np.mean(_val0_mean_list[114:152])

    #     _std_half0 = np.std(_val0_mean_list[0:38])
    #     _std_half1 = np.std(_val0_mean_list[38:76])
    #     _std_half2 = np.std(_val0_mean_list[76:114])
    #     _std_half3 = np.std(_val0_mean_list[114:152])

    #     scan2_res_global_means.append([_mean_half0, _mean_half1, _mean_half2, _mean_half3])
    #     scan2_res_global_errs.append([_std_half0, _std_half1, _std_half2, _std_half3])

    # scan2_inv_ref = initial_inv_vref_list.copy()
    # scan2_noinv_ref = initial_noinv_vref_list.copy()

    # for _half in range(4):
    #     _best_mean = 9999
    #     _best_index = 0
    #     for _index in range(len(scan2_res_global_means)):
    #         _mean_diff = abs(scan2_res_global_means[_index][_half] - scan2_target)
    #         if _mean_diff < _best_mean:
    #             _best_mean = _mean_diff
    #             _best_index = _index
    #     scan2_inv_ref[_half] = int(scan2_res_global_means[_best_index][_half])

    # logger.debug(f"Scan 2 results: {scan2_inv_ref}")

    # for _asic in range(total_asic):
    #     _ref_voltage_half0 = default_reference_voltage.copy()
    #     _ref_voltage_half1 = default_reference_voltage.copy()

    #     _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((int(scan2_inv_ref[_asic*2]) & 0x03) << 2) | (scan2_noinv_ref[_asic*2] & 0x03)
    #     _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((int(scan2_inv_ref[_asic*2+1]) & 0x03) << 2) | (scan2_noinv_ref[_asic*2+1] & 0x03)

    #     _ref_voltage_half0[4] = int(scan2_inv_ref[_asic*2]) >> 2
    #     _ref_voltage_half1[4] = int(scan2_inv_ref[_asic*2 + 1]) >> 2
    #     _ref_voltage_half0[5] = scan2_noinv_ref[_asic*2] >> 2
    #     _ref_voltage_half1[5] = scan2_noinv_ref[_asic*2 + 1] >> 2

    #     if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=3, verbose=i2c_setting_verbose):
    #         logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")
        
    #     if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=3, verbose=i2c_setting_verbose):
    #         logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

    # # ! --- Scan 3 for channel trim correlation ---
    # progress_bar_scan_3 = tqdm(range(0, 64, chn_trim_scan_step_fine))
    # scan3_res_chn_means = []
    # scan3_res_chn_errs  = []
    # for _trim in progress_bar_scan_3:
    #     progress_bar_scan_3.set_description(f"Channel Trim " + "{:02d}".format(_trim))
    #     _chn_wise = default_channel_wise.copy()
    #     _chn_wise[3] = (_trim << 2) & 0xFC  # trim inv
    #     # _chn_wise[0] = _trim & 0x3F  # input dac

    #     for _asic in range(total_asic):
    #         packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=_chn_wise, retry=3, verbose=i2c_setting_verbose)

    #         packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=_chn_wise, retry=3, verbose=i2c_setting_verbose)

    #     # ! --- Data reading sequence ---
    #     for _asic in range(2):
    #         if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
    #             logger.warning(f"Failed to turn on LR for ASIC {_asic}")

    #     packetlib.clean_socket(socket_udp)

    #     if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
    #         logger.warning("Failed to start the generator")

    #     extracted_payloads_pool = []
    #     event_fragment_pool     = []

    #     expected_event_num = gen_nr_cycle

    #     current_half_packet_num = 0
    #     current_event_num = 0

    #     all_chn_value_0_array = np.zeros((expected_event_num, 152))
    #     all_chn_value_1_array = np.zeros((expected_event_num, 152))
    #     all_chn_value_2_array = np.zeros((expected_event_num, 152))
    #     hamming_code_array    = np.zeros((expected_event_num, 12))

    #     while True:
    #         try:
    #             data_packet, rec_addr    = socket_udp.recvfrom(8192)
    #             # logger.debug("Packet received")
    #             extracted_payloads_pool += packetlib.extract_raw_payloads(data_packet)
    #             while len(extracted_payloads_pool) >= 5:
    #                 candidate_packet_lines = extracted_payloads_pool[:5]
    #                 is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
    #                 if is_packet_good:
    #                     event_fragment_pool.append(event_fragment)
    #                     current_half_packet_num += 1
    #                     extracted_payloads_pool = extracted_payloads_pool[5:]
    #                 else:
    #                     logger.warning("Warning: Event fragment is not good")
    #                     extracted_payloads_pool = extracted_payloads_pool[1:]
    #             indices_to_delete = set()
    #             if len(event_fragment_pool) >= 4:
    #                 event_fragment_pool = sorted(event_fragment_pool, key=lambda x: x[0][3:7])
    #             i = 0
    #             while i <= len(event_fragment_pool) - 4:
    #                 timestamp0 = event_fragment_pool[i][0][4] << 24 | event_fragment_pool[i][0][5] << 16 | event_fragment_pool[i][0][6] << 8 | event_fragment_pool[i][0][7]
    #                 timestamp1 = event_fragment_pool[i+1][0][4] << 24 | event_fragment_pool[i+1][0][5] << 16 | event_fragment_pool[i+1][0][6] << 8 | event_fragment_pool[i+1][0][7]
    #                 timestamp2 = event_fragment_pool[i+2][0][4] << 24 | event_fragment_pool[i+2][0][5] << 16 | event_fragment_pool[i+2][0][6] << 8 | event_fragment_pool[i+2][0][7]
    #                 timestamp3 = event_fragment_pool[i+3][0][4] << 24 | event_fragment_pool[i+3][0][5] << 16 | event_fragment_pool[i+3][0][6] << 8 | event_fragment_pool[i+3][0][7]
    #                 str_timestamp = f"{timestamp0:08X} {timestamp1:08X} {timestamp2:08X} {timestamp3:08X}"
    #                 if timestamp0 == timestamp1 and timestamp0 == timestamp2 and timestamp0 == timestamp3:
    #                     for _half in range(4):
    #                         extracted_data = packetlib.assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
    #                         extracted_values = packetlib.extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
    #                         uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
    #                         for j in range(len(extracted_values["_extracted_values"])):
    #                             all_chn_value_0_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
    #                             all_chn_value_1_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
    #                             all_chn_value_2_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
    #                         hamming_code_array[current_event_num][_half*3+0] =  packetlib.DaqH_get_H1(extracted_values["_DaqH"])
    #                         hamming_code_array[current_event_num][_half*3+1] =  packetlib.DaqH_get_H2(extracted_values["_DaqH"])
    #                         hamming_code_array[current_event_num][_half*3+2] =  packetlib.DaqH_get_H3(extracted_values["_DaqH"])
    #                     indices_to_delete.update([i, i+1, i+2, i+3])
    #                     current_event_num += 1
    #                     i += 4
    #                 else:
    #                     i += 1
    #                     # logger.debug(f"Timestamp: {str_timestamp}")
    #             for index in sorted(indices_to_delete, reverse=True):
    #                 del event_fragment_pool[index]
    #                 # logger.debug("current event num:" + str(current_event_num))
    #             if current_event_num == expected_event_num:
    #                 break;
                            
    #         except Exception as e:
    #             logger.warning("Exception in receiving data")
    #             logger.warning(e)
    #             logger.warning('Packet received: ' + str(current_half_packet_num))
    #             logger.warning('left fragments:' + str(len(event_fragment_pool)))
    #             logger.warning("current event num:" + str(current_event_num))
    #             measurement_good_flag = False
    #             break

    #     if not np.all(hamming_code_array == 0):
    #         logger.warning("Hamming code error detected!")
    #         measurement_good_flag = False

    #     if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
    #         logger.warning("Failed to stop the generator")

    #     for _asic in range(2):
    #         if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
    #             logger.warning(f"Failed to turn off LR for ASIC {_asic}")

    #     _val0_mean_list = []
    #     _val0_err_list  = []
    #     for _chn in range(152):
    #         _candidate_values = []
    #         for _event in range(expected_event_num):
    #             if np.all(hamming_code_array[_event] == 0):
    #                 _candidate_values.append(all_chn_value_0_array[_event][_chn])
    #         if len(_candidate_values) > 0:
    #             _val0_mean_list.append(np.mean(_candidate_values))
    #             _val0_err_list.append(np.std(_candidate_values))
    #         else:
    #             logger.warning(f"Channel {_chn} has no valid data")
    #             _val0_mean_list.append(0)
    #             _val0_err_list.append(0)
                    
    #     scan3_res_chn_means.append(_val0_mean_list)
    #     scan3_res_chn_errs.append(_val0_err_list)

    # final_ref_inv_list = scan2_inv_ref.copy()
    # final_ref_noinv_list = scan2_noinv_ref.copy()
    # # * Find the best channel trim value
    # target_trim_output = max_initial_value.copy()
    # chn_trim_values = np.zeros(152)

    # for _chn in range(152):
    #     if _chn in channel_not_used or _chn in dead_channels:
    #         continue
    #     _best_mean = 9999
    #     _best_index = 0
    #     for _index in range(len(scan3_res_chn_means)):
    #         _mean_diff = abs(scan3_res_chn_means[_index][_chn] - target_trim_output[_chn//38])
    #         if _mean_diff < _best_mean:
    #             _best_mean = _mean_diff
    #             _best_index = _index
    #     chn_trim_values[_chn] = int(list(range(0, 64, chn_trim_scan_step_fine))[_best_index])

    # logger.debug(f"Channel trim values: {chn_trim_values}")

    # for _chn in range(152):
    #     _chn_wise = default_channel_wise.copy()
    #     _chn_wise[3] = int(chn_trim_values[_chn]) << 2
    #     # _chn_wise[0] = chn_trim_values[_chn] & 0x3F

    #     _asic = _chn // 76
    #     _half = (_chn % 76) // 38

    #     _sub_addr = packetlib.uni_chn_to_subblock_list[_chn % 76]

    #     if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=3, verbose=i2c_setting_verbose):
    #         logger.warning(f"Failed to set ChannelWise settings for ASIC {_asic}")

    # # ! --- Data reading sequence ---
    # for _asic in range(2):
    #     if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
    #         logger.warning(f"Failed to turn on LR for ASIC {_asic}")

    # packetlib.clean_socket(socket_udp)

    # if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
    #     logger.warning("Failed to start the generator")

    # extracted_payloads_pool = []
    # event_fragment_pool     = []

    # expected_event_num = gen_nr_cycle

    # current_half_packet_num = 0
    # current_event_num = 0

    # all_chn_value_0_array = np.zeros((expected_event_num, 152))
    # all_chn_value_1_array = np.zeros((expected_event_num, 152))
    # all_chn_value_2_array = np.zeros((expected_event_num, 152))
    # hamming_code_array    = np.zeros((expected_event_num, 12))

    # while True:
    #     try:
    #         data_packet, rec_addr    = socket_udp.recvfrom(8192)
    #         # logger.debug("Packet received")
    #         extracted_payloads_pool += packetlib.extract_raw_payloads(data_packet)
    #         while len(extracted_payloads_pool) >= 5:
    #             candidate_packet_lines = extracted_payloads_pool[:5]
    #             is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
    #             if is_packet_good:
    #                 event_fragment_pool.append(event_fragment)
    #                 current_half_packet_num += 1
    #                 extracted_payloads_pool = extracted_payloads_pool[5:]
    #             else:
    #                 logger.warning("Warning: Event fragment is not good")
    #                 extracted_payloads_pool = extracted_payloads_pool[1:]
    #         indices_to_delete = set()
    #         if len(event_fragment_pool) >= 4:
    #             event_fragment_pool = sorted(event_fragment_pool, key=lambda x: x[0][3:7])
    #         i = 0
    #         while i <= len(event_fragment_pool) - 4:
    #             timestamp0 = event_fragment_pool[i][0][4] << 24 | event_fragment_pool[i][0][5] << 16 | event_fragment_pool[i][0][6] << 8 | event_fragment_pool[i][0][7]
    #             timestamp1 = event_fragment_pool[i+1][0][4] << 24 | event_fragment_pool[i+1][0][5] << 16 | event_fragment_pool[i+1][0][6] << 8 | event_fragment_pool[i+1][0][7]
    #             timestamp2 = event_fragment_pool[i+2][0][4] << 24 | event_fragment_pool[i+2][0][5] << 16 | event_fragment_pool[i+2][0][6] << 8 | event_fragment_pool[i+2][0][7]
    #             timestamp3 = event_fragment_pool[i+3][0][4] << 24 | event_fragment_pool[i+3][0][5] << 16 | event_fragment_pool[i+3][0][6] << 8 | event_fragment_pool[i+3][0][7]
    #             str_timestamp = f"{timestamp0:08X} {timestamp1:08X} {timestamp2:08X} {timestamp3:08X}"
    #             if timestamp0 == timestamp1 and timestamp0 == timestamp2 and timestamp0 == timestamp3:
    #                 for _half in range(4):
    #                     extracted_data = packetlib.assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
    #                     extracted_values = packetlib.extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
    #                     uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
    #                     for j in range(len(extracted_values["_extracted_values"])):
    #                         all_chn_value_0_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
    #                         all_chn_value_1_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
    #                         all_chn_value_2_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
    #                     hamming_code_array[current_event_num][_half*3+0] =  packetlib.DaqH_get_H1(extracted_values["_DaqH"])
    #                     hamming_code_array[current_event_num][_half*3+1] =  packetlib.DaqH_get_H2(extracted_values["_DaqH"])
    #                     hamming_code_array[current_event_num][_half*3+2] =  packetlib.DaqH_get_H3(extracted_values["_DaqH"])
    #                 indices_to_delete.update([i, i+1, i+2, i+3])
    #                 current_event_num += 1
    #                 i += 4
    #             else:
    #                 i += 1
    #                 # logger.debug(f"Timestamp: {str_timestamp}")
    #         for index in sorted(indices_to_delete, reverse=True):
    #             del event_fragment_pool[index]
    #             # logger.debug("current event num:" + str(current_event_num))
    #         if current_event_num == expected_event_num:
    #             break;
                            
    #     except Exception as e:
    #         logger.warning("Exception in receiving data")
    #         logger.warning(e)
    #         logger.warning('Packet received: ' + str(current_half_packet_num))
    #         logger.warning('left fragments:' + str(len(event_fragment_pool)))
    #         logger.warning("current event num:" + str(current_event_num))
    #         measurement_good_flag = False
    #         break

    # if not np.all(hamming_code_array == 0):
    #     logger.warning("Hamming code error detected!")
    #     measurement_good_flag = False
    # if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0,daq_start_stop=0x00, verbose=False):
    #     logger.warning("Failed to stop the generator")
    # for _asic in range(2):
    #     if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
    #         logger.warning(f"Failed to turn off LR for ASIC {_asic}")

    # _val0_mean_list = []
    # _val0_err_list  = []

    # for _chn in range(152):
    #     _candidate_values = []
    #     for _event in range(expected_event_num):
    #         if np.all(hamming_code_array[_event] == 0):
    #             _candidate_values.append(all_chn_value_0_array[_event][_chn])
    #     if len(_candidate_values) > 0:
    #         _val0_mean_list.append(np.mean(_candidate_values))
    #         _val0_err_list.append(np.std(_candidate_values))
    #     else:
    #         logger.warning(f"Channel {_chn} has no valid data")
    #         _val0_mean_list.append(0)
    #         _val0_err_list.append(0)

    # fig_scan3, ax_scan3 = plt.subplots(1, 1, figsize=(10, 6))
    # ax_scan3.errorbar(range(152), _val0_mean_list, yerr=_val0_err_list)
    # ax_scan3.set_xlabel('Channel')
    # ax_scan3.set_ylabel('Mean Value')
    # ax_scan3.set_title('Channel Trim Scan')
    # plt.savefig(os.path.join(output_dump_folder, 'ChannelPedestalScan3.png'))

    # final_chn_trim_list = chn_trim_values.copy()
    
    # plot the results

    fig_scan1, ax_scan1 = plt.subplots(1, 1, figsize=(10, 6))
    ax_scan1.errorbar(range(152), _val0_mean_list, yerr=_val0_err_list)
    ax_scan1.set_xlabel('Channel')
    ax_scan1.set_ylabel('Mean Value')
    ax_scan1.set_title('Channel Trim Scan')
    plt.savefig(os.path.join(output_dump_folder, 'ChannelPedestalScan1.png'))

    # fig_global, ax_global = plt.subplots(1, 1, figsize=(10, 6))
    # for _half in range(4):
    #     _half_means = []
    #     _half_errs  = []
    #     for _index in range(len(scan0_res_global_means)):
    #         _half_means.append(scan0_res_global_means[_index][_half])
    #         _half_errs.append(scan0_res_global_errs[_index][_half])
    #     ax_global.errorbar(range(0, 1024, ref_inv_scan_step_corse), _half_means, yerr=_half_errs, label=f'Half {_half}')
    # ax_global.set_xlabel('Inv Ref Value')
    # ax_global.set_ylabel('Mean Value')
    # ax_global.set_title('Inv Ref Scan')
    # ax_global.legend()
    # plt.savefig(os.path.join(output_dump_folder, 'InvRefScan.png'))


finally:
    socket_udp.close()

output_pedecalib_json["inv_vref_list"] = final_ref_inv_list
output_pedecalib_json["noinv_vref_list"] = final_ref_noinv_list
# save np array
output_pedecalib_json["chn_trim_settings"] = final_chn_trim_list.tolist()

output_pedecalib_json["dead_channels"] = dead_channels
output_pedecalib_json["channel_not_used"] = channel_not_used

with open(output_pedecalib_path, 'w') as f:
    json.dump(output_pedecalib_json, f, indent=4)
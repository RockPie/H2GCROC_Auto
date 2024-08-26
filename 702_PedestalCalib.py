import packetlib
import socket
import numpy as np
import time
import json
import os
from loguru import logger
import matplotlib.pyplot as plt

from tqdm import tqdm

# * --- Set up script information -------------------------------------
script_id_str       = '702_PedestalCalib2'
script_version_str  = '1.0'

# * --- Test function -------------------------------------------------
def measure_v0(_socket_udp, _ip, _port, _fpga_address, _reg_runLR, _reg_offLR, _event_num, _fragment_life, _logger):
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
    for _chn in range(152):
        _candidate_values = []
        for _event in range(_event_num):
            if np.all(hamming_code_array[_event] == 0):
                _candidate_values.append(all_chn_value_0_array[_event][_chn])
        if len(_candidate_values) > 0:
            _val0_mean_list.append(np.mean(_candidate_values))
            _val0_err_list.append(np.std(_candidate_values))
        else:
            _logger.warning(f"Channel {_chn} has no valid data")
            _val0_mean_list.append(0)
            _val0_err_list.append(0)
    return _val0_mean_list, _val0_err_list

def chn_pedestal_draw(_mean_list, _err_list, _title, _y_max=512):
    fig, ax = plt.subplots()
    ax.errorbar(range(152), _mean_list, yerr=_err_list)
    ax.set_title(_title)
    ax.set_xlabel('Channel Number')
    ax.set_ylabel('Pedestal Value [ADC]')
    ax.set_ylim(0, _y_max)
    fig.tight_layout()
    return fig

# * --- Set up logging ------------------------------------------------
# Define a custom sink that uses tqdm to write log messages
class TqdmSink:
    def __init__(self):
        self.level = "DEBUG"

    def write(self, message):
        tqdm.write(message.rstrip())  # Remove the trailing newline

# Remove the default logger configuration
logger.remove()

# Add the custom tqdm sink with colored formatting for different levels
logger.add(
    TqdmSink(), 
    format="<green>{time:HH:mm:ss}</green> - "
           "<level>{level: <8}</level> - "
           "<level>{message}</level>",
    level="DEBUG",
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# * --- Set up output folder -------------------------------------------
output_dump_path = 'dump'   # dump is for temporary files like config
output_data_path = 'data'   # data is for very-likely-to-be-used files
config_to_modify = 'config/default_2024Aug_config.json'

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
timeout         = 2 # seconds

if is_common_settings_exist:
    try:
        udp_settings = common_settings['udp']
        h2gcroc_ip = udp_settings['h2gcroc_ip']
        pc_ip = udp_settings['pc_ip']
        h2gcroc_port = udp_settings['h2gcroc_port']
        pc_port = udp_settings['pc_port']
    except KeyError:
        logger.warning("Common settings file does not contain UDP settings")

config_json = json.load(open(config_to_modify, 'r'))
if config_json["UDP Settings"]["IP Address"] != h2gcroc_ip:
    logger.warning(f"Config file IP address is not the same as the common settings: {config_json['UDP Settings']['IP Address']} vs {h2gcroc_ip}")
if config_json["UDP Settings"]["Port"] != str(h2gcroc_port):
    logger.warning(f"Config file port is not the same as the common settings: {config_json['UDP Settings']['Port']} vs {h2gcroc_port}")

logger.info(f"UDP settings: H2GCROC IP: {h2gcroc_ip}, PC IP: {pc_ip}, H2GCROC Port: {h2gcroc_port}, PC Port: {pc_port}")

output_config_json['udp'] = {
    'h2gcroc_ip': h2gcroc_ip,
    'pc_ip': pc_ip,
    'h2gcroc_port': h2gcroc_port,
    'pc_port': pc_port,
    'timeout': timeout
}

output_pedecalib_json['udp'] = {
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

inputdac_step = 2

target_pedestal = 80

dead_chn_std_threshold = 5


ref_inv_scan_range = range(100, 700, 10)
trim_scan_range = range(0, 64, 2)

# half pedestal default values:
initial_inv_vref_list   = [300,200,300,300]
initial_noinv_vref_list = [800,800,800,800]

i2c_setting_verbose = False

output_pedecalib_json['running_parameters'] = {
    'total_asic': total_asic,
    'fpga_address': fpga_address,
    'target_pedestal': target_pedestal,
    'fragment_life': fragment_life,
    'channel_not_used': channel_not_used,
    'dead_channels': dead_channels,
    'gen_nr_cycle': gen_nr_cycle,
    'gen_interval_value': gen_interval_value,
    'gen_fcmd_internal_injection': gen_fcmd_internal_injection,
    'gen_fcmd_L1A': gen_fcmd_L1A,
    'i2c_setting_verbose': i2c_setting_verbose
}

initial_chn_pede_list   = []
initial_chn_err_list    = []

final_ref_inv_list      = []
final_ref_noinv_list    = []
final_chn_trim_list     = []
final_chn_inputdac_list = []

try:
# * --- Set up the generator --------------------------------------------------
    if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0x00, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=0, gen_pre_interval = 10, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=75, gen_fcmd=75,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=0x00, verbose=False):
        logger.warning(f"Failed to set up the generator")
# * --- Set up the I2C settings -----------------------------------------------
    for _asic in range(total_asic):

        # * --- Global_Analog_0 & Global_Analog_1 ---
        _global_analog = default_global_analog.copy()

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=_global_analog, retry=5, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Global_Analog_0 settings for ASIC {_asic}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=_global_analog, retry=5, verbose=i2c_setting_verbose):
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

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=5, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=5, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

        # * --- Channel Wise ---
        _chn_wise = default_channel_wise.copy()
        packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=_chn_wise, retry=5, verbose=i2c_setting_verbose)
        packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=_chn_wise, retry=5, verbose=i2c_setting_verbose)

    # ! --- Get the initial pedestal values ---
    initial_chn_pede_list, initial_chn_pede_err = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)
    _fig = chn_pedestal_draw(initial_chn_pede_list, initial_chn_pede_err, f"Initial Pedestal Values")
    _fig.savefig(os.path.join(output_dump_folder, f"pede_initial.png"))

    target_chn_inputdac_list = [0,0,0,0]
    # set as the largest value for each half
    for _chn in range(152):
        if _chn not in channel_not_used and _chn not in dead_channels:
            if initial_chn_pede_list[_chn] > target_chn_inputdac_list[_chn//38]:
                target_chn_inputdac_list[_chn//38] = initial_chn_pede_list[_chn]

    logger.debug(f"Target input DAC values: {target_chn_inputdac_list}")

    # ! === InputDAC setting ==================================================

    inputdac_chn_pede_list = initial_chn_pede_list.copy()
    inputdac_chn_err_list = initial_chn_pede_err.copy()
    final_chn_inputdac_list = [0]*152

    progress_bar_inputdac = tqdm(range(20))
    for _retry in progress_bar_inputdac:
        progress_bar_inputdac.set_description(f"InputDAC Try {_retry+1}")
        _changed_chn_cnt = 0
        for _chn in range(152):
            if _chn not in channel_not_used and _chn not in dead_channels:
                if inputdac_chn_pede_list[_chn] < target_chn_inputdac_list[_chn//38]:
                    final_chn_inputdac_list[_chn] += inputdac_step
                    _asic_num = _chn // 76
                    _chn_num  = _chn % 76
                    _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

                    _chn_wise = default_channel_wise.copy()
                    _chn_wise[0] = final_chn_inputdac_list[_chn] & 0x3F

                    if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                        logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num}")

                    _changed_chn_cnt += 1

        if _changed_chn_cnt == 0:
            break

        time.sleep(0.2)

        inputdac_chn_pede_list, inputdac_chn_err_list = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)
        
    fig_res_inputdac = chn_pedestal_draw(inputdac_chn_pede_list, inputdac_chn_err_list, f"InputDAC Pedestal Results")
    fig_res_inputdac.savefig(os.path.join(output_dump_folder, f"pede_inputdac.png"))
    for _chn in range(152):
        if _chn not in channel_not_used and _chn not in dead_channels:
            if (target_chn_inputdac_list[_chn//38] - inputdac_chn_pede_list[_chn]) > 200:
                final_chn_inputdac_list[_chn] = 0
                dead_channels.append(_chn)

    if len(dead_channels) > 0:
        logger.warning(f"Dead channels found after InputDAC setting: {dead_channels}")

# ! === initial_inv setting ==================================================
    final_ref_inv_list = initial_inv_vref_list.copy()
    final_ref_noinv_list = initial_noinv_vref_list.copy()

    progress_bar_inv = tqdm(ref_inv_scan_range)
    scan_ref_inv_res_global_means = []
    scan_ref_inv_res_global_errs  = []
    for _ref_inv in progress_bar_inv:
        progress_bar_inv.set_description(f"InvRef: {_ref_inv}")

        for _asic in range(total_asic):
            _ref_voltage_half0 = default_reference_voltage.copy()
            _ref_voltage_half1 = default_reference_voltage.copy()

            _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((_ref_inv & 0x03) << 2) | (final_ref_noinv_list[_asic*2] & 0x03)
            _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((_ref_inv & 0x03) << 2) | (final_ref_noinv_list[_asic*2+1] & 0x03)

            _ref_voltage_half0[4] = _ref_inv >> 2
            _ref_voltage_half1[4] = _ref_inv >> 2

            _ref_voltage_half0[5] = initial_noinv_vref_list[_asic*2] >> 2
            _ref_voltage_half1[5] = initial_noinv_vref_list[_asic*2 + 1] >> 2

            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=5, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=5, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

        time.sleep(0.2)

        _inv_chn_pede_list, _inv_chn_err_list = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)

        _global_mean = [0,0,0,0]
        _global_err  = [0,0,0,0]
        _valid_chn_cnt = [0,0,0,0]

        for _chn in range(152):
            if _chn not in channel_not_used and _chn not in dead_channels:
                _global_mean[_chn//38] += _inv_chn_pede_list[_chn]
                _valid_chn_cnt[_chn//38] += 1

        for _half in range(4):
            _global_mean[_half] /= _valid_chn_cnt[_half]

        for _chn in range(152):
            if _chn not in channel_not_used and _chn not in dead_channels:
                _global_err[_chn//38] += (_inv_chn_pede_list[_chn] - _global_mean[_chn//38])**2

        for _half in range(4):
            _global_err[_half] = np.sqrt(_global_err[_half] / _valid_chn_cnt[_half])

        scan_ref_inv_res_global_means.append(_global_mean)
        scan_ref_inv_res_global_errs.append(_global_err)

    fig_global, ax_global = plt.subplots(1, 1, figsize=(10, 6))
    for _half in range(4):
        _half_means = []
        _half_errs  = []
        for _scan in range(len(ref_inv_scan_range)):
            _half_means.append(scan_ref_inv_res_global_means[_scan][_half])
            _half_errs.append(scan_ref_inv_res_global_errs[_scan][_half])
        ax_global.errorbar(ref_inv_scan_range, _half_means, yerr=_half_errs, label=f'Half {_half}')
    ax_global.set_xlabel('Inv Ref Value')
    ax_global.set_ylabel('Mean Value')
    ax_global.set_title('Inv Ref Scan')
    ax_global.legend()
    plt.savefig(os.path.join(output_dump_folder, 'InvRefScan.png'))

    # find the best inv ref value for target pedestal
    for _half in range(4):
        _best_inv_ref_index = 0
        _dist_min = 1024
        for _scan in range(len(ref_inv_scan_range)):
            if np.abs(scan_ref_inv_res_global_means[_scan][_half] - target_pedestal) < _dist_min:
                _best_inv_ref_index = _scan
                _dist_min = np.abs(scan_ref_inv_res_global_means[_scan][_half] - target_pedestal)
        _best_inv_ref = ref_inv_scan_range[_best_inv_ref_index]


        final_ref_inv_list[_half] = _best_inv_ref

    logger.debug(f"Final Inv Ref Values: {final_ref_inv_list}")

    # set the final inv ref values
    for _asic in range(total_asic):
        _ref_voltage_half0 = default_reference_voltage.copy()
        _ref_voltage_half1 = default_reference_voltage.copy()

        _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((final_ref_inv_list[_asic*2] & 0x03) << 2) | (final_ref_noinv_list[_asic*2] & 0x03)
        _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((final_ref_inv_list[_asic*2+1] & 0x03) << 2) | (final_ref_noinv_list[_asic*2+1] & 0x03)

        _ref_voltage_half0[4] = final_ref_inv_list[_asic*2] >> 2
        _ref_voltage_half1[4] = final_ref_inv_list[_asic*2 + 1] >> 2
        _ref_voltage_half0[5] = final_ref_noinv_list[_asic*2] >> 2
        _ref_voltage_half1[5] = final_ref_noinv_list[_asic*2 + 1] >> 2

        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=5, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")
        
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=5, verbose=i2c_setting_verbose):
            logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

    _temp_chn_pede_list, _temp_chn_pede_err = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)
    _fig = chn_pedestal_draw(_temp_chn_pede_list, _temp_chn_pede_err, f"Pedestal After Ref Inv")
    _fig.savefig(os.path.join(output_dump_folder, f"pede_ref_inv.png"))
    
# ! === Channel trim setting ==================================================

    trim_target = [0,0,0,0]
    scan_trim_res_chn_means = []
    scan_trim_res_chn_errs  = []

    for _chn in range(152):
        if _chn not in channel_not_used and _chn not in dead_channels:
            _half = _chn // 38
            if _temp_chn_pede_list[_chn] > trim_target[_half]:
                trim_target[_half] = _temp_chn_pede_list[_chn]

    progress_bar_trim = tqdm(trim_scan_range)
    for _trim in progress_bar_trim:
        progress_bar_trim.set_description(f"Trim: {_trim}")

        for _chn in range(152):
            if _chn not in channel_not_used and _chn not in dead_channels:
                _asic_num = _chn // 76
                _chn_num  = _chn % 76
                _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

                _chn_wise = default_channel_wise.copy()
                _chn_wise[0] = final_chn_inputdac_list[_chn] & 0x3F
                _chn_wise[3] = (_trim << 2) & 0xFC

                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                    logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num}")

        time.sleep(0.2)

        _trim_chn_pede_list, _trim_chn_err_list = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)

        scan_trim_res_chn_means.append(_trim_chn_pede_list)
        scan_trim_res_chn_errs.append(_trim_chn_err_list)

    scan_trim_std_list = []
    for _chn in range(152):
        if _chn not in channel_not_used and _chn not in dead_channels:
            _mean_list = []
            for _scan in range(len(trim_scan_range)):
                _mean_list.append(scan_trim_res_chn_means[_scan][_chn])
            _std = np.std(_mean_list)
            scan_trim_std_list.append(_std)
            if _std < dead_chn_std_threshold:
                dead_channels.append(_chn)
                logger.warning(f"Channel {_chn} is dead (trim std < {dead_chn_std_threshold})")

    # plot the std of each channel
    fig_trim_std, ax_trim_std = plt.subplots(1, 1, figsize=(10, 6))
    ax_trim_std.hist(scan_trim_std_list, bins=40, range=(0, max(scan_trim_std_list)))
    ax_trim_std.set_xlabel('Standard Deviation')
    ax_trim_std.set_ylabel('Channel Count')
    ax_trim_std.set_title('Trim Scan Standard Deviation')
    fig_trim_std.savefig(os.path.join(output_dump_folder, 'TrimScanStd.png'))

    # plot the pedestal-trim curve for some channels
    fig_trim, ax_trim = plt.subplots(1, 1, figsize=(10, 6))
    for _chn in range(130, 140):
        if _chn not in channel_not_used and _chn not in dead_channels:
            _mean_list = []
            _err_list = []
            for _scan in range(len(trim_scan_range)):
                _mean_list.append(scan_trim_res_chn_means[_scan][_chn])
                _err_list.append(scan_trim_res_chn_errs[_scan][_chn])
            ax_trim.errorbar(trim_scan_range, _mean_list, yerr=_err_list, label=f'Chn {_chn}')
    ax_trim.set_xlabel('Trim Value')
    ax_trim.set_ylabel('Mean Value [ADC]')
    ax_trim.set_title('Trim Scan')
    ax_trim.legend()
    fig_trim.savefig(os.path.join(output_dump_folder, 'TrimScan.png'))

    # find channels with max pede still less than target
    for _chn in range(152):
        if _chn not in channel_not_used and _chn not in dead_channels:
            if (trim_target[_chn//38] - scan_trim_res_chn_means[-1][_chn]) > 200:
                dead_channels.append(_chn)
                logger.warning(f"Channel {_chn} is dead (max pede < target)")

    # * Find the best channel trim value
    final_chn_trim_list = [0]*152
    for _chn in range(152):
        if _chn not in channel_not_used and _chn not in dead_channels:
            _best_trim_index = 0
            _dist_min = 1024
            for _scan in range(len(trim_scan_range)):
                if np.abs(scan_trim_res_chn_means[_scan][_chn] - trim_target[_chn//38]) < _dist_min:
                    _best_trim_index = _scan
                    _dist_min = np.abs(scan_trim_res_chn_means[_scan][_chn] - trim_target[_chn//38])
            _best_trim = trim_scan_range[_best_trim_index]
            final_chn_trim_list[_chn] = _best_trim
    
    logger.debug(f"Final Trim Values: {final_chn_trim_list}")

    # * Set the final trim values
    for _chn in range(152):
        if _chn not in channel_not_used and _chn not in dead_channels:
            _asic_num = _chn // 76
            _chn_num  = _chn % 76
            _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

            _chn_wise = default_channel_wise.copy()
            _chn_wise[0] = final_chn_inputdac_list[_chn] & 0x3F
            _chn_wise[3] = (final_chn_trim_list[_chn] << 2) & 0xFC

            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num}")

    _trim_chn_pede_list, _trim_chn_pede_err = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)
    _fig = chn_pedestal_draw(_trim_chn_pede_list, _trim_chn_pede_err, f"Pedestal After Trim")
    _fig.savefig(os.path.join(output_dump_folder, f"pede_trim.png"))

# ! === Ref inv tuning ==================================================

    _ref_inv_tunning_retry = 20
    _ref_inv_tunning_step = 2
    progress_bar_ref_tune = tqdm(range(_ref_inv_tunning_retry))
    for _retry in progress_bar_ref_tune:
        progress_bar_ref_tune.set_description(f"Ref Inv Tune Try {_retry+1}")
        ref_inv_tunning_res = [0,0,0,0]
        ref_inv_tunning_counter = [0,0,0,0]

        for _chn in range(152):
            if _chn not in channel_not_used and _chn not in dead_channels:
                _half = _chn // 38
                ref_inv_tunning_res[_half] += _trim_chn_pede_list[_chn]
                ref_inv_tunning_counter[_half] += 1
    
        for _half in range(4):
            if ref_inv_tunning_counter[_half] == 0:
                ref_inv_tunning_res[_half] = 0
            else:
                ref_inv_tunning_res[_half] /= ref_inv_tunning_counter[_half]

        _changed_half_cnt = 0
        for _half in range(4):
            if ref_inv_tunning_res[_half] > target_pedestal + 2:
                final_ref_inv_list[_half] += _ref_inv_tunning_step
                if final_ref_inv_list[_half] > 1023:
                    final_ref_inv_list[_half] = 1023
                _changed_half_cnt += 1
            elif ref_inv_tunning_res[_half] < target_pedestal - 2:
                final_ref_inv_list[_half] -= _ref_inv_tunning_step
                if final_ref_inv_list[_half] < 0:
                    final_ref_inv_list[_half] = 0
                _changed_half_cnt += 1

        if _changed_half_cnt == 0:
            progress_bar_ref_tune.set_description(f"Ref Inv Tune Done")
            break

        for _asic in range(total_asic):
            _ref_voltage_half0 = default_reference_voltage.copy()
            _ref_voltage_half1 = default_reference_voltage.copy()

            _ref_voltage_half0[1] = ( _ref_voltage_half0[1] & 0xF0) | ((final_ref_inv_list[_asic*2] & 0x03) << 2) | (final_ref_noinv_list[_asic*2] & 0x03)
            _ref_voltage_half1[1] = ( _ref_voltage_half1[1] & 0xF0) | ((final_ref_inv_list[_asic*2+1] & 0x03) << 2) | (final_ref_noinv_list[_asic*2+1] & 0x03)

            _ref_voltage_half0[4] = final_ref_inv_list[_asic*2] >> 2
            _ref_voltage_half1[4] = final_ref_inv_list[_asic*2 + 1] >> 2
            _ref_voltage_half0[5] = final_ref_noinv_list[_asic*2] >> 2
            _ref_voltage_half1[5] = final_ref_noinv_list[_asic*2 + 1] >> 2

            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_voltage_half0, retry=5, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_Half_0 settings for ASIC {_asic}")
            if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_voltage_half1, retry=5, verbose=i2c_setting_verbose):
                logger.warning(f"Failed to set Reference_Voltage_Half_1 settings for ASIC {_asic}")

        time.sleep(0.2)

        _trim_chn_pede_list, _trim_chn_pede_err = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)

        if _retry == _ref_inv_tunning_retry - 1:
            logger.warning(f"Ref inv tuning did not converge after {_ref_inv_tunning_retry} tries")

    _fig = chn_pedestal_draw(_trim_chn_pede_list, _trim_chn_pede_err, f"Pedestal After Ref Inv Tuning")
    _fig.savefig(os.path.join(output_dump_folder, f"pede_ref_inv_tune.png"))

# ! === Final Pedestal Tunning ==========================================

    _final_trim_tunning_retry = 15
    _final_trim_tunning_step = 2

    progress_bar_final_tune = tqdm(range(_final_trim_tunning_retry))
    for _retry in progress_bar_final_tune:
        progress_bar_final_tune.set_description(f"Final Trim Tune Try {_retry+1}")

        _changed_chn_cnt = 0
        for _chn in range(152):
            if _chn not in channel_not_used and _chn not in dead_channels:
                if _trim_chn_pede_list[_chn] > target_pedestal + 2:
                    final_chn_trim_list[_chn] -= _final_trim_tunning_step
                    if final_chn_trim_list[_chn] < 0:
                        final_chn_trim_list[_chn] = 0
                        # dead_channels.append(_chn)
                    _changed_chn_cnt += 1
                    _asic_num = _chn // 76
                    _chn_num  = _chn % 76
                    _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

                    _chn_wise = default_channel_wise.copy()
                    _chn_wise[0] = final_chn_inputdac_list[_chn] & 0x3F
                    _chn_wise[3] = (final_chn_trim_list[_chn] << 2) & 0xFC

                    if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                        logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num}")
                elif _trim_chn_pede_list[_chn] < target_pedestal - 2:
                    final_chn_trim_list[_chn] += _final_trim_tunning_step
                    if final_chn_trim_list[_chn] > 63:
                        final_chn_trim_list[_chn] = 63
                        # dead_channels.append(_chn)
                    _changed_chn_cnt += 1
                    _asic_num = _chn // 76
                    _chn_num  = _chn % 76
                    _sub_addr = packetlib.uni_chn_to_subblock_list[_chn_num]

                    _chn_wise = default_channel_wise.copy()
                    _chn_wise[0] = final_chn_inputdac_list[_chn] & 0x3F
                    _chn_wise[3] = (final_chn_trim_list[_chn] << 2) & 0xFC

                    if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_wise, retry=5, verbose=False):
                        logger.warning(f"Failed to set Channel Wise settings for ASIC {_asic_num}")

        if _changed_chn_cnt == 0:
            progress_bar_final_tune.set_description(f"Final Trim Tune Done")
            break
        # else:
        #     logger.debug(f"Changed channel count: {_changed_chn_cnt}")

        time.sleep(0.2)

        _trim_chn_pede_list, _trim_chn_pede_err = measure_v0(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, top_reg_runLR, top_reg_offLR, gen_nr_cycle, fragment_life, logger)

    _fig = chn_pedestal_draw(_trim_chn_pede_list, _trim_chn_pede_err, f"Final Pedestal")
    _fig.savefig(os.path.join(output_dump_folder, f"pede_final.png"))

    if len(dead_channels) > 0:
        logger.warning(f"Dead channels found after final tuning: {dead_channels}")

finally:
    socket_udp.close()


output_pedecalib_json["inv_vref_list"]          = final_ref_inv_list
output_pedecalib_json["noinv_vref_list"]        = final_ref_noinv_list
output_pedecalib_json["chn_trim_settings"]      = final_chn_trim_list
output_pedecalib_json["chn_inputdac_settings"]  = final_chn_inputdac_list
output_pedecalib_json["dead_channels"]          = dead_channels
output_pedecalib_json["channel_not_used"]       = channel_not_used
output_pedecalib_json["pede_values"]            = _trim_chn_pede_list

with open(output_pedecalib_path, 'w') as f:
    json.dump(output_pedecalib_json, f, indent=4)

with open(output_config_path, 'w') as f:
    json.dump(output_config_json, f, indent=4)
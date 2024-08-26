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
script_id_str       = '101_IODelay'
script_version_str  = '0.5'

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

output_folder_name      = f'{script_id_str}_data_{time.strftime("%Y%m%d_%H%M%S")}'
output_config_json_name = f'{script_id_str}_config_{time.strftime("%Y%m%d_%H%M%S")}.json'
output_config_json = {}

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

# * --- Set running parameters ----------------------------------------
total_asic          = 2
asic_select         = 0x03
fpga_address        = int(h2gcroc_ip.split('.')[-1]) - 208
locked_output       = 0xaccccccc
sublist_min_len     = 20
sublist_extend      = 8
inter_step_sleep    = 0.05 # seconds

enable_sublist          = True
enable_reset            = True

i2c_setting_verbose     = False
bitslip_verbose         = False
bitslip_debug_verbose   = False

output_config_json['running_parameters'] = {
    'total_asic': total_asic,
    'asic_select': asic_select,
    'fpga_address': fpga_address,
    'locked_output': locked_output,
    'sublist_min_len': sublist_min_len,
    'sublist_extend': sublist_extend,
    'inter_step_sleep': inter_step_sleep,
    'enable_sublist': enable_sublist,
    'enable_reset': enable_reset,
    'i2c_setting_verbose': i2c_setting_verbose,
    'bitslip_verbose': bitslip_verbose,
    'bitslip_debug_verbose': bitslip_debug_verbose
}

# * --- Useful functions ----------------------------------------------
def find_true_sublists(bool_list):
    results = []
    start_index = None
    in_sequence = False

    for index, value in enumerate(bool_list):
        if value:
            if not in_sequence:
                # Starting a new sequence
                start_index = index
                in_sequence = True
        else:
            if in_sequence:
                # Ending a sequence
                results.append((start_index, index - start_index))
                in_sequence = False

    # Check if the last sequence extends to the end of the list
    if in_sequence:
        results.append((start_index, len(bool_list) - start_index))

    return results

def test_delay(delay_val, num_asic, verbose=False):
    if not packetlib.set_bitslip(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_addr=fpga_address, asic_num=num_asic, io_dly_sel=asic_select, a0_io_dly_val_fclk=0x000, a0_io_dly_val_fcmd=0x400, a1_io_dly_val_fclk=0x000, a1_io_dly_val_fcmd=0x400, a0_io_dly_val_tr0=delay_val, a0_io_dly_val_tr1=delay_val, a0_io_dly_val_tr2=delay_val, a0_io_dly_val_tr3=delay_val, a0_io_dly_val_dq0=delay_val, a0_io_dly_val_dq1=delay_val, a1_io_dly_val_tr0=delay_val, a1_io_dly_val_tr1=delay_val, a1_io_dly_val_tr2=delay_val, a1_io_dly_val_tr3=delay_val, a1_io_dly_val_dq0=delay_val, a1_io_dly_val_dq1=delay_val, verbose=bitslip_verbose):
        print('\033[33m' + "Warning in setting bitslip 0" + '\033[0m')
    if not packetlib.send_reset_adj(socket_udp, h2gcroc_ip, h2gcroc_port,fpga_addr=fpga_address, asic_num=num_asic, sw_hard_reset_sel=0x00, sw_hard_reset=0x00,sw_soft_reset_sel=0x00, sw_soft_reset=0x00, sw_i2c_reset_sel=0x00,sw_i2c_reset=0x00, reset_pack_counter=0x00, adjustable_start=asic_select,verbose=False):
        print('\033[33m' + "Warning in sending reset_adj" + '\033[0m')
    time.sleep(inter_step_sleep)
    debug_info = packetlib.get_debug_data(socket_udp, h2gcroc_ip, h2gcroc_port,fpga_addr=fpga_address, asic_num=num_asic, verbose=bitslip_debug_verbose)
    if debug_info is None:
        print('\033[33m' + "Warning in getting debug data" + '\033[0m')
    else:
        print_str = "Delay " + "{:03}".format(delay_val) + ": "
        all_locked = True
        if debug_info["trg0_value"] == locked_output:
            if verbose:
                print_str += '\033[32m' + "T0 " + '\033[0m'
        else:
            if verbose:
                print_str += '\033[31m' + "T0 " + '\033[0m'
            all_locked = False
        if debug_info["trg1_value"] == locked_output:
            if verbose:
                print_str += '\033[32m' + "T1 " + '\033[0m'
        else:
            if verbose:
                print_str += '\033[31m' + "T1 " + '\033[0m'
            all_locked = False
        if debug_info["trg2_value"] == locked_output:
            if verbose:
                print_str += '\033[32m' + "T2 " + '\033[0m'
        else:
            if verbose:
                print_str += '\033[31m' + "T2 " + '\033[0m'
            all_locked = False
        if debug_info["trg3_value"] == locked_output:
            if verbose:
                print_str += '\033[32m' + "T3 " + '\033[0m'
        else:
            if verbose:
                print_str += '\033[31m' + "T3 " + '\033[0m'
            all_locked = False
        if debug_info["data0_value"] == locked_output:
            if verbose:
                print_str += '\033[32m' + "D0 " + '\033[0m'
        else:
            if verbose:
                print_str += '\033[31m' + "D0 " + '\033[0m'
            all_locked = False
        if debug_info["data1_value"] == locked_output:
            if verbose:
                print_str += '\033[32m' + "D1 " + '\033[0m'
        else:
            if verbose:
                print_str += '\033[31m' + "D1 " + '\033[0m'
            all_locked = False
        if verbose:
            print(print_str)
    return all_locked

# * --- I2C settings --------------------------------------------------
i2c_content_top = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x05,0x00]
i2c_content_digital_half_0 = [0x00,0x00,0x00,0x00,0x80,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x19,0x00,0x0a,0xcc,0xcc,0xcc,0x0c,0xcc,0xcc,0xcc,0xcc,0x0f,0x02,0x00]
i2c_content_digital_half_1 = [0x00,0x00,0x00,0x00,0x80,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x19,0x00,0x0a,0xcc,0xcc,0xcc,0x0c,0xcc,0xcc,0xcc,0xcc,0x0f,0x02,0x00]
i2c_content_global_analog_0 =[0x6f,0xdb,0x83,0x28,0x28,0x28,0x9a,0x9a,0xa8,0x8a,0x40,0x4a,0x4b,0x68]
i2c_content_global_analog_1 =[0x6f,0xdb,0x83,0x28,0x28,0x28,0x9a,0x9a,0xa8,0x8a,0x40,0x4a,0x4b,0x68]
i2c_content_master_tdc_0 = [0x37,0xd4,0x54,0x80,0x0a,0xd4,0x03,0x00,0x80,0x80,0x0a,0x95,0x03,0x00,0x40,0x00]
i2c_content_master_tdc_1 = [0x37,0xd4,0x54,0x80,0x0a,0xd4,0x03,0x00,0x80,0x80,0x0a,0x95,0x03,0x00,0x40,0x00]
i2c_content_reference_voltage_0 = [0xb4,0x0a,0xfa,0xfa,0xb8,0xd4,0xda,0x42,0x00,0x00]
i2c_content_reference_voltage_1 = [0xb4,0x0e,0xfa,0xfa,0xad,0xd4,0xda,0x42,0x00,0x00]
i2c_content_half_wise_0 = [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]
i2c_content_half_wise_1 = [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]

output_config_json['i2c_settings'] = {
    'i2c_content_top': i2c_content_top,
    'i2c_content_digital_half_0': i2c_content_digital_half_0,
    'i2c_content_digital_half_1': i2c_content_digital_half_1,
    'i2c_content_global_analog_0': i2c_content_global_analog_0,
    'i2c_content_global_analog_1': i2c_content_global_analog_1,
    'i2c_content_master_tdc_0': i2c_content_master_tdc_0,
    'i2c_content_master_tdc_1': i2c_content_master_tdc_1,
    'i2c_content_reference_voltage_0': i2c_content_reference_voltage_0,
    'i2c_content_reference_voltage_1': i2c_content_reference_voltage_1,
    'i2c_content_half_wise_0': i2c_content_half_wise_0,
    'i2c_content_half_wise_1': i2c_content_half_wise_1
}

try:
    for _asic in range(total_asic):
        logger.info(f"Setting I2C for ASIC {_asic} ...")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=i2c_content_top,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Top")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=i2c_content_digital_half_0,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Digital_Half_0")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=i2c_content_digital_half_1,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Digital_Half_1")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=i2c_content_global_analog_0,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Global_Analog_0")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=i2c_content_global_analog_1,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Global_Analog_1")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Master_TDC_0"], reg_addr=0x00, data=i2c_content_master_tdc_0,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Master_TDC_0")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Master_TDC_1"], reg_addr=0x00, data=i2c_content_master_tdc_1,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Master_TDC_1")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=i2c_content_reference_voltage_0,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Reference_Voltage_0")
        if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=i2c_content_reference_voltage_1,retry=3, verbose=i2c_setting_verbose):
            logger.warning(f"Readback mismatch for ASIC {_asic} Reference_Voltage_1")
        # ! HalfWise will not read back correctly
        packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=i2c_content_half_wise_0,retry=3, verbose=i2c_setting_verbose)
        packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=i2c_content_half_wise_1,retry=3, verbose=i2c_setting_verbose)

# * --- Main script ---------------------------------------------------
    if enable_reset:
        for _asic in range(total_asic):
            if not packetlib.send_reset_adj(socket_udp, h2gcroc_ip, h2gcroc_port,fpga_addr=fpga_address, asic_num=_asic, sw_hard_reset_sel=0x00, sw_hard_reset=0x00,sw_soft_reset_sel=0x03, sw_soft_reset=0x01, sw_i2c_reset_sel=0x00,sw_i2c_reset=0x00, reset_pack_counter=0x00, adjustable_start=0x00,verbose=False):
                logger.critical("Error in resetting ASIC " + str(_asic))
                exit()
    
    best_values = []
    for _asic in range(total_asic):
        locked_flag_array  = []
        locked_delay_array = []
        logger.info(f"Setting bitslip for ASIC {_asic}")
        progress_bar_local = tqdm(range(0, 512, 2))
        for _delay in progress_bar_local:
            if _delay == 320: # Skip 320 because it is cursed
                continue
            progress_bar_local.set_description(f"Delay " + "{:03}".format(_delay))
            locked_flag_array.append(test_delay(_delay, _asic, verbose=False))
            locked_delay_array.append(_delay)
        valid_sublists = []
        try:
            valid_sublists = find_true_sublists(locked_flag_array)
        except:
            logger.error('No valid IO delay found for ASIC ' + str(_asic))
            continue
        if len(valid_sublists) == 0:
            logger.error('No valid IO delay found for ASIC ' + str(_asic))
            continue

        sorted_sublists = sorted(valid_sublists, key=lambda x: x[1], reverse=True)
        _valid_sublist_found = False
        _best_delay = 0
        logger.info(f"Searching for best IO delay for ASIC {_asic}")
        for _sublist_index in range(len(sorted_sublists)):
            _sublist = sorted_sublists[_sublist_index]
            # logger.info(f"Sublist start index: {_sublist[0]}, length: {_sublist[1]}")
            if len(_sublist) != 2:
                logger.warning(f"Abnormal sublist data format for ASIC {_asic}")
                break
            _start_index = _sublist[0]
            _sublist_len = _sublist[1]
            if _sublist_len < sublist_min_len:
                _best_delay = _start_index + _sublist_len // 2
                _valid_sublist_found = True
                logger.warning('No best IO delay found for ASIC ' + str(_asic)+ ' using coarse delay ' + str(_best_delay))
                break
            if not enable_sublist:
                _best_delay = _start_index + _sublist_len // 2
                _valid_sublist_found = True
                break
            else:
                _subscan_start = max(0, _start_index - sublist_extend)
                _subscan_end = min(511, _start_index + _sublist_len + sublist_extend)

            valid_subsublists = []
            locked_flag_sublist = []
            locked_delay_sublist = []
            progress_bar_sublocal = tqdm(range(_subscan_start, _subscan_end, 1))
            for _subdelay in progress_bar_sublocal:
                if _subdelay == 320:
                    continue
                progress_bar_sublocal.set_description(f"Delay " + "{:03}".format(_subdelay))
                locked_flag_sublist.append(test_delay(_subdelay, _asic, verbose=False))
                locked_delay_sublist.append(_subdelay)
            try:
                valid_subsublists = find_true_sublists(locked_flag_sublist)
            except:
                continue
                # _best_delay = _start_index + _sublist_len // 2
                # _valid_sublist_found = True
                # logger.warning('No best IO delay found for ASIC ' + str(_asic)+ ' using coarse delay ' + str(_best_delay) + ' (E1)')
                # break
            if len(valid_subsublists) == 0:
                continue
                # _best_delay = _start_index + _sublist_len // 2
                # _valid_sublist_found = True
                # logger.warning('No best IO delay found for ASIC ' + str(_asic)+ ' using coarse delay ' + str(_best_delay) + ' (E2)')
                # break
            sorted_subsublists = sorted(valid_subsublists, key=lambda x: x[1], reverse=True)
            # logger.info(sorted_subsublists)
            try:
                best_sublist = sorted_subsublists[0]
            except:
                continue
            if best_sublist[1] > sublist_min_len:
                _best_delay = best_sublist[0] + best_sublist[1] // 2 + _subscan_start
                _valid_sublist_found = True
                break
            else:
                if _sublist_index == len(sorted_sublists) - 1:
                    _best_delay = _start_index + _sublist_len // 2
                    _valid_sublist_found = True
                    logger.warning('No best IO delay found for ASIC ' + str(_asic)+ ' using coarse delay ' + str(_best_delay) + ' (E4)')
                    break
                else:
                    continue
        if not _valid_sublist_found:
            logger.error('No valid IO delay found for ASIC ' + str(_asic))
            continue
        if not test_delay(_best_delay, _asic, verbose=False):
            logger.error(f"Best IO delay candidate for ASIC {_asic} is not locked")
            continue
        else:
            logger.info(f"Best IO delay for ASIC {_asic}: {_best_delay}")
            best_values.append(_best_delay)

finally:
    socket_udp.close()

output_config_json['best_values'] = best_values

with open(output_config_path, 'w') as json_file:
    json.dump(output_config_json, json_file, indent=4)

logger.info(f"Configuration saved to {output_config_path}")
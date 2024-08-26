import packetlib
import socket
from tqdm import tqdm
import time
import json
import os

# * UDP Settings
# * ---------------------------------------------------------------------------

output_file_path = "dump"
output_json_name = "iodelay_config_" + time.strftime("%Y%m%d_%H%M%S") + ".json"
output_json_path = os.path.join(output_file_path, output_json_name)
output_json = {}

if not os.path.exists(output_file_path):
    os.makedirs(output_file_path)

common_settings_json_path = "common_settings.json"
with open(common_settings_json_path, 'r') as json_file:
    common_settings = json.load(json_file)
udp_settings = common_settings["udp"]

h2gcroc_ip      = "10.1.2.208"
pc_ip           = "10.1.2.207"
h2gcroc_port    = 11000
pc_port         = 11000

if "h2gcroc_ip" in udp_settings:
    h2gcroc_ip = udp_settings["h2gcroc_ip"]
if "pc_ip" in udp_settings:
    pc_ip = udp_settings["pc_ip"]
if "h2gcroc_port" in udp_settings:
    h2gcroc_port = udp_settings["h2gcroc_port"]
if "pc_port" in udp_settings:
    pc_port = udp_settings["pc_port"]

output_json["udp"] = {}
output_json["udp"]["h2gcroc_ip"]    = h2gcroc_ip
output_json["udp"]["pc_ip"]         = pc_ip
output_json["udp"]["h2gcroc_port"]  = h2gcroc_port
output_json["udp"]["pc_port"]       = pc_port

socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_udp.bind((pc_ip, pc_port))

# * Parameters
# * ---------------------------------------------------------------------------
total_asic      = 2
fpga_address    = 0x00
locked_output   = 0xaccccccc
sublist_min_len = 3
sublist_extend  = 8
inter_step_sleep= 0.05

i2c_setting_verbose     = False
bitslip_verbose         = False
bitslip_debug_verbose   = False
debug_verbose           = False

output_json["options"] = {}
output_json["options"]["total_asic"]        = total_asic
output_json["options"]["fpga_address"]      = fpga_address
output_json["options"]["locked_output"]     = locked_output
output_json["options"]["sublist_min_len"]   = sublist_min_len
output_json["options"]["sublist_extend"]    = sublist_extend
output_json["options"]["inter_step_sleep"]  = inter_step_sleep

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
    if not packetlib.set_bitslip(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_addr=fpga_address, asic_num=num_asic, io_dly_sel=ASIC_SELECT, a0_io_dly_val_fclk=0x000, a0_io_dly_val_fcmd=0x400, a1_io_dly_val_fclk=0x000, a1_io_dly_val_fcmd=0x400, a0_io_dly_val_tr0=delay_val, a0_io_dly_val_tr1=delay_val, a0_io_dly_val_tr2=delay_val, a0_io_dly_val_tr3=delay_val, a0_io_dly_val_dq0=delay_val, a0_io_dly_val_dq1=delay_val, a1_io_dly_val_tr0=delay_val, a1_io_dly_val_tr1=delay_val, a1_io_dly_val_tr2=delay_val, a1_io_dly_val_tr3=delay_val, a1_io_dly_val_dq0=delay_val, a1_io_dly_val_dq1=delay_val, verbose=bitslip_verbose):
        print('\033[33m' + "Warning in setting bitslip 0" + '\033[0m')
    if not packetlib.send_reset_adj(socket_udp, h2gcroc_ip, h2gcroc_port,fpga_addr=fpga_address, asic_num=num_asic, sw_hard_reset_sel=0x00, sw_hard_reset=0x00,sw_soft_reset_sel=0x00, sw_soft_reset=0x00, sw_i2c_reset_sel=0x00,sw_i2c_reset=0x00, reset_pack_counter=0x00, adjustable_start=ASIC_SELECT,verbose=False):
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
    

# * Get and print the status of the device
# * ---------------------------------------------------------------------------
data_packet = packetlib.pack_data_req_status(0xA0, 0x00)
socket_udp.sendto(data_packet, (h2gcroc_ip, h2gcroc_port))
received_data, addr = socket_udp.recvfrom(1024)
unpacked_data = packetlib.unpack_data_rpy_status(received_data)
output_json["status"] = unpacked_data

# * Reset the device
# * ---------------------------------------------------------------------------
for asic in range(total_asic):
    if not packetlib.send_reset_adj(socket_udp, h2gcroc_ip, h2gcroc_port,fpga_addr=fpga_address, asic_num=asic, sw_hard_reset_sel=0x00, sw_hard_reset=0x00,sw_soft_reset_sel=0x03, sw_soft_reset=0x01, sw_i2c_reset_sel=0x00,sw_i2c_reset=0x00, reset_pack_counter=0x00, adjustable_start=0x00,verbose=False):
        print('\033[33m' + "Warning in sending reset_adj" + '\033[0m')

# * Write the config to all ASICs
# * ---------------------------------------------------------------------------
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

output_json["i2c_config"] = {}
output_json["i2c_config"]["i2c_content_top"] = i2c_content_top
output_json["i2c_config"]["i2c_content_digital_half_0"] = i2c_content_digital_half_0
output_json["i2c_config"]["i2c_content_digital_half_1"] = i2c_content_digital_half_1
output_json["i2c_config"]["i2c_content_global_analog_0"] = i2c_content_global_analog_0
output_json["i2c_config"]["i2c_content_global_analog_1"] = i2c_content_global_analog_1
output_json["i2c_config"]["i2c_content_master_tdc_0"] = i2c_content_master_tdc_0
output_json["i2c_config"]["i2c_content_master_tdc_1"] = i2c_content_master_tdc_1
output_json["i2c_config"]["i2c_content_reference_voltage_0"] = i2c_content_reference_voltage_0
output_json["i2c_config"]["i2c_content_reference_voltage_1"] = i2c_content_reference_voltage_1
output_json["i2c_config"]["i2c_content_half_wise_0"] = i2c_content_half_wise_0
output_json["i2c_config"]["i2c_content_half_wise_1"] = i2c_content_half_wise_1

for test_loop_counter in range(1):
    for i in range(total_asic):
        print('\033[34m' + "Setting i2c content for ASIC " + str(i) + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=i2c_content_top, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=i2c_content_top, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Top" + '\033[0m')
            else:
                print('\033[32m' + "Fixed sending i2c content for Top" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=i2c_content_digital_half_0, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=i2c_content_digital_half_0, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Digital_Half_0" + '\033[0m')
            else:
                print('\033[32m' + "Fixed sending i2c content for Digital_Half_0" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=i2c_content_digital_half_1, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=i2c_content_digital_half_1, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Digital_Half_1" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=i2c_content_global_analog_0, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=i2c_content_global_analog_0, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Global_Analog_0" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=i2c_content_global_analog_1, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=i2c_content_global_analog_1, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Global_Analog_1" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Master_TDC_0"], reg_addr=0x00, data=i2c_content_master_tdc_0, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Master_TDC_0"], reg_addr=0x00, data=i2c_content_master_tdc_0, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Master_TDC_0" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Master_TDC_1"], reg_addr=0x00, data=i2c_content_master_tdc_1, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Master_TDC_1"], reg_addr=0x00, data=i2c_content_master_tdc_1, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Master_TDC_1" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=i2c_content_reference_voltage_0, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=i2c_content_reference_voltage_0, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Reference_Voltage_0" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=i2c_content_reference_voltage_1, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=i2c_content_reference_voltage_1, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Reference_Voltage_1" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=i2c_content_half_wise_0, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=i2c_content_half_wise_0, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Half_Wise_0" + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=i2c_content_half_wise_1, verbose=i2c_setting_verbose):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=i2c_content_half_wise_1, verbose=i2c_setting_verbose):
                print('\033[33m' + "Warning in sending i2c content for Half_Wise_1" + '\033[0m')

time.sleep(0.5)

# soft reset



ASIC_SELECT  = 3
locked_flag_array  = []
locked_delay_array = []
best_delay_value_array = []
longest_locked_array = []
for i in range(total_asic):
    print('\033[34m' + "Setting bitslip for ASIC " + str(i) + '\033[0m')
    progress_bar_local = tqdm(range(0, 512, 4))
    for delay_input in progress_bar_local:
        if delay_input == 320:
            continue
        progress_bar_local.set_description("Delay " + '{:03}'.format(delay_input))
        locked_flag_array.append(test_delay(delay_input, i, verbose=debug_verbose))
        locked_delay_array.append(delay_input)
    valid_sublists = find_true_sublists(locked_flag_array)
    if len(valid_sublists) == 0:
        print('\033[31m' + "No valid sublists found for ASIC " + str(i) + '\033[0m')
        continue
    sorted_valid_sublists = sorted(valid_sublists, key=lambda x: x[1], reverse=True)

    # * Look into each sublists and use smaller step size to find the best delay
    # * ---------------------------------------------------------------------------
    print('\033[34m' + "Finding the best delay value" + '\033[0m')
    for list_index in range(len(sorted_valid_sublists)):
        sublist = sorted_valid_sublists[list_index]
        start_index = sublist[0]
        length = sublist[1]
        if length < sublist_min_len:
            print('\033[31m' + "No valid sublists found for ASIC " + str(i) + '\033[0m')
            break
        start_delay = locked_delay_array[start_index] - sublist_extend
        end_delay = locked_delay_array[start_index + length - 1] + sublist_extend
        # best_delay = (start_delay + sublist_extend) // 2
        # test_delay(best_delay, i, verbose=False)
        # break
        if start_delay < 0:
            start_delay = 0
        if end_delay > 512:
            end_delay = 512
        valid_subsublists       = []
        locked_flag_sub_array   = []
        locked_delay_sub_array  = []
        progress_bar_local = tqdm(range(start_delay, end_delay, 1))
        for delay_input in progress_bar_local:
            if delay_input == 320:
                continue
            progress_bar_local.set_description("Delay " + '{:03}'.format(delay_input))
            locked_flag_sub_array.append(test_delay(delay_input, i, verbose=False))
            locked_delay_sub_array.append(delay_input)
        valid_subsublists = find_true_sublists(locked_flag_sub_array)
        sorted_valid_sublists = sorted(valid_subsublists, key=lambda x: x[1], reverse=True)
        try:
            longest_length = sorted_valid_sublists[0][1]
        except:
            print('\033[31m' + "No valid sublists found for potential list " + str(list_index) + " for ASIC " + str(i) + '\033[0m')
            print(sorted_valid_sublists)
            longest_length = 0
            continue
        if list_index == len(sorted_valid_sublists) - 1:
            if longest_length < sublist_min_len:
                print('\033[31m' + "No valid sublists found for ASIC " + str(i) + '\033[0m')
                break
            else:
                best_delay = locked_delay_sub_array[sorted_valid_sublists[0][0] + sorted_valid_sublists[0][1] // 2]
                print('\033[32m' + "Best delay for ASIC " + str(i) + " is " + str(best_delay) + '\033[0m')
                print('\033[32m' + "Longest locked status " + str(i) + " is " + str(longest_length) + '\033[0m')
                best_delay_value_array.append(best_delay)
                longest_locked_array.append(longest_length)
                test_delay(best_delay, i, verbose=False)
                break
        else:
            if longest_length < sublist_min_len:
                continue
            else:
                if longest_length > sorted_valid_sublists[list_index + 1][1]:
                    best_delay = locked_delay_sub_array[sorted_valid_sublists[0][0] + sorted_valid_sublists[0][1] // 2]
                    print('\033[32m' + "Best delay for ASIC " + str(i) + " is " + str(best_delay) + '\033[0m')
                    print('\033[32m' + "Longest locked status " + str(i) + " is " + str(longest_length) + '\033[0m')
                    best_delay_value_array.append(best_delay)
                    longest_locked_array.append(longest_length)
                    test_delay(best_delay, i, verbose=False)
                    break
                else:
                    continue

# * Write the best delay value to the json file
# * ---------------------------------------------------------------------------

output_json["best_delay_value"] = best_delay_value_array
output_json["longest_locked"] = longest_locked_array

with open(output_json_path, 'w') as json_file:
    json.dump(output_json, json_file, indent=4)

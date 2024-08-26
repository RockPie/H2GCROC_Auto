import packetlib
import socket
import numpy as np
import time
import json
import os

from tqdm import tqdm
import matplotlib.pyplot as plt

# * UDP Settings
# * ---------------------------------------------------------------------------
output_file_path = "dump"
output_data_file_path = "data"
output_json_name = "ex_delay_scan_config_" + time.strftime("%Y%m%d_%H%M%S") + ".json"

output_json_path = os.path.join(output_file_path, output_json_name)
output_json = {}

output_data_file_folder = "ex_delay_scan_" + time.strftime("%Y%m%d_%H%M%S")

output_data_file_path  = os.path.join(output_data_file_path, output_data_file_folder)

if not os.path.exists(output_file_path):
    os.makedirs(output_file_path)

if not os.path.exists(output_data_file_path):
    os.makedirs(output_data_file_path)

common_settings_json_path = "common_settings.json"
with open(common_settings_json_path, 'r') as json_file:
    common_settings = json.load(json_file)
udp_settings = common_settings["udp"]

h2gcroc_ip      = "10.1.2.208"
pc_ip           = "10.1.2.207"
h2gcroc_port    = 11000
pc_port         = 11000

udp_receive_timeout = 10

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
output_json["udp"]["udp_receive_timeout"] = udp_receive_timeout

socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_udp.bind((pc_ip, pc_port))
# socket_udp.settimeout(udp_receive_timeout)

# * Parameters
# * ---------------------------------------------------------------------------
total_asic                  = 2
fpga_address                = 0x00
machine_gun_val             = 14
gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011
gen_pre_inverval_value      = 200
gen_nr_cycle                = 1
gen_interval_value          = 100
_ex_trg_val = 2 # TODO: Fixed external trigger value
# _L1_delay_value = 8 # TODO: Fixed L1 delay value

if gen_nr_cycle*(1+machine_gun_val)*4 > 300:
    print('\033[33m' + "Warning: Too much packet requested" + '\033[0m')

# ex_trg_delay_range = range(0,10,10)
ex_trg_delay_trg_max = 100
ex_trg_delay_event_max = ex_trg_delay_trg_max * (machine_gun_val+1)

L1_offset_scan_range = range(0, 10, 10)

# * Read I2C settings
# * ---------------------------------------------------------------------------
i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

top_reg_runLR = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
top_reg_offLR = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
HV_on = [0xA0, 0x00, 0x03, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
while len(HV_on) < 40:
    HV_on.append(0x00)
HV_on = bytes(HV_on)

socket_udp.sendto(HV_on, (h2gcroc_ip, h2gcroc_port))

default_channel_wise    = reg_settings.get_default_reg_content('registers_channel_wise')
default_ref_content     = reg_settings.get_default_reg_content('registers_reference_voltage')
default_digital_content = reg_settings.get_default_reg_content('registers_digital_half')
default_global_analog   = reg_settings.get_default_reg_content('registers_global_analog')

output_json["i2c"] = {}
output_json["i2c"]["top_reg_runLR"] = top_reg_runLR
output_json["i2c"]["top_reg_offLR"] = top_reg_offLR

# * Find the newest pedestal calibration file
# * ---------------------------------------------------------------------------
pedestal_calib_file_prefix = "pede_calib_config"
pedestal_calib_folder = "dump"
pedestal_calib_files = [f for f in os.listdir(pedestal_calib_folder) if f.startswith(pedestal_calib_file_prefix)]
pedestal_calib_files.sort(reverse=True)
if len(pedestal_calib_files) > 0:
    newest_pedestal_calib_file = pedestal_calib_files[0]
    print("Newest pedestal calibration file: " + newest_pedestal_calib_file)

trim_dac_values     = []
_noinv_vref_list    = []
_inv_vref_list      = []

with open(os.path.join(pedestal_calib_folder, newest_pedestal_calib_file), 'r') as json_file:
    pedestal_calib      = json.load(json_file)
    _noinv_vref_list    = pedestal_calib["noinv_vref_list"]
    _inv_vref_list      = pedestal_calib["inv_vref_list"]
    trim_dac_values     = pedestal_calib["chn_trim_settings"]

if len(_noinv_vref_list) == 0 or len(_inv_vref_list) == 0:
    print("Error: No pedestal calibration data")
    exit()

try:

    # * Get and print the status of the device
    # * ---------------------------------------------------------------------------
    data_packet = packetlib.pack_data_req_status(0xA0, 0x00)
    socket_udp.sendto(data_packet, (h2gcroc_ip, h2gcroc_port))
    received_data, addr = socket_udp.recvfrom(1024)
    unpacked_data = packetlib.unpack_data_rpy_status(received_data)
    if unpacked_data is not None:
        output_json["status"] = unpacked_data

    # * Setup channels
    # * ---------------------------------------------------------------------------
    for _chn in range(2*76):
        _sub_addr = packetlib.uni_chn_to_subblock_list[_chn % 76]
        _half_num = _chn // 38
        _asic_num = _chn // 76

        _chn_content =default_channel_wise.copy()
        _chn_content[3] = (int(trim_dac_values[_chn]) << 2) & 0xFC
        # _chn_content[4] = 0x04 # TODO: Disable internal injection mode
        _chn_content[14] = 0xC0

        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=False):
                if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=False):
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')
                else:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')

    # * Setup reference and digital half
    # * ---------------------------------------------------------------------------
    for _asic in range(2):
        _digital_content = default_digital_content.copy()
        _digital_content[4]  = 0xC0 # to force calibration mode
        _digital_content[25] = 0x02 # bx offset, just to make sure it is consistent with N.N's setting

        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_content, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_content, verbose=False):
                print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=_digital_content, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=_digital_content, verbose=False):
                print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

        _global_analog = default_global_analog.copy()
        _global_analog[8]  = 0xA0
        _global_analog[9]  = 0xCA
        _global_analog[10] = 0x42
        _global_analog[14] = 0x6F

        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=_global_analog, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_0"], reg_addr=0x00, data=_global_analog, verbose=False):
                print('\033[33m' + "Warning: I2C global analog readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
        
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=_global_analog, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Global_Analog_1"], reg_addr=0x00, data=_global_analog, verbose=False):
                print('\033[33m' + "Warning: I2C global analog readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
                
    for _asic in range(2):
        _ref_content_half0 = default_ref_content.copy()
        _ref_content_half1 = default_ref_content.copy()
        _ref_content_half0[4] = _inv_vref_list[_asic*2] >> 2
        _ref_content_half1[4] = _inv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[5] = _noinv_vref_list[_asic*2] >> 2
        _ref_content_half1[5] = _noinv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((_inv_vref_list[_asic*2] & 0x03) << 2) | (_noinv_vref_list[_asic*2] & 0x03)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((_inv_vref_list[_asic*2+1] & 0x03) << 2) | (_noinv_vref_list[_asic*2+1] & 0x03)
        _ref_content_half0[10] = 0x07 # ! just to make sure it is consistent with N.N's setting
        _ref_content_half1[10] = 0x07

        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=False):
                print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=False):
                print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')



    # * Do lots of reading
    # * ---------------------------------------------------------------------------

    measurement_good_array = []

    for _L1_delay_value in tqdm(L1_offset_scan_range):
        output_data_txt_name = "ex_delay_scan_data_val_" + str(_L1_delay_value) + "_" + time.strftime("%Y%m%d_%H%M%S") + ".txt"
        read_data_saving_path = os.path.join(output_data_file_path, output_data_txt_name)
        with open(read_data_saving_path, 'w') as data_file:
            _trg_dead_time = _ex_trg_val + machine_gun_val + 10
            if _trg_dead_time >= 256:
                print('Warning: Ex trigger dead time out of range')
                _trg_dead_time = 255
            for _asic in range(2):
                _digital_content = default_digital_content.copy()
                _digital_content[4]  = 0xC0 # to force calibration mode
                _digital_content[25] = 0x02 # bx offset, just to make sure it is consistent with N.N's setting
                _digital_content[15] = _L1_delay_value

                if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_content, verbose=False):
                    if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_content, verbose=False):
                        print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
                    else:
                        print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

                if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_1"], reg_addr=0x00, data=_digital_content, verbose=False):
                    if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Digital_Half_0"], reg_addr=0x00, data=_digital_content, verbose=False):
                        print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
                    else:
                        print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
                        
            if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, 0, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=0, gen_pre_interval = gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=gen_fcmd_internal_injection,ext_trg_en=1, ext_trg_delay=_ex_trg_val, ext_trg_deadtime=_trg_dead_time, gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val,verbose=False):
                print('\033[33m' + "Warning: Generator parameters not match" + '\033[0m')

            for asic in range(2):
                if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, verbose=False):
                    if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, verbose=False):
                        print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(asic) + '\033[0m')

            measurement_good_flag = True
            # Send start stop
            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0xFF, verbose=False):
                print('\033[33m' + "Warning in sending DAQ Push" + '\033[0m')

            # for asic in range(2):
            #     packetlib.read_save_all_i2c('i2c_debug_info_'+ str(asic) + '_' + str(_L1_delay_value) + '.txt', socket_udp, h2gcroc_ip, h2gcroc_port, asic, fpga_address)

            extracted_payloads_pool = []
            event_fragment_pool     = []

            expected_half_packet_num = ex_trg_delay_event_max * 4
            expected_event_num = ex_trg_delay_event_max
            current_half_packet_num = 0
            current_event_num = 0

            all_chn_value_0_array = np.zeros((expected_event_num, 152))
            all_chn_value_1_array = np.zeros((expected_event_num, 152))
            all_chn_value_2_array = np.zeros((expected_event_num, 152))
            hamming_code_array = np.zeros((expected_event_num, 12))

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
                            extracted_payloads_pool = extracted_payloads_pool[5:]
                            hex_data = ' '.join(b.hex() for b in event_fragment)
                            data_file.write(hex_data + '\n')
                        else:
                            print('\033[33m' + "Warning: Event fragment is not good" + '\033[0m')
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
                    print("current event num:" + str(current_event_num))
                    # print('left fragments:' + str(len(event_fragment_pool)))
                    if current_event_num == expected_event_num:
                        break;
                        
                except Exception as e:
                    print('\033[33m' + "Warning: Exception in receiving data" + '\033[0m')
                    print(e)
                    print('Packet expected: ' + str(expected_half_packet_num))
                    print('Packet received: ' + str(current_half_packet_num))
                    print('left fragments:' + str(len(event_fragment_pool)))
                    print("current event num:" + str(current_event_num))
                    measurement_good_flag = False
                    break

            # check if hamming code is all 0
            if not np.all(hamming_code_array == 0):
                print("Hamming code error!")
                measurement_good_flag = False

            measurement_good_array.append(measurement_good_flag)
            # ! Core code finish -------------------------------------------------------------

            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
                print('\033[33m' + "Warning in sending DAQ Push" + '\033[0m')

            for asic in range(2):
                if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, verbose=False):
                    print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(asic) + '\033[0m')
finally:
    socket_udp.close()



true_count = sum(measurement_good_array)  # 'True' is counted as 1, 'False' as 0
total_count = len(measurement_good_array)
true_percentage = (true_count / total_count) * 100

print(f"Percentage of True values: {true_percentage:.2f}%")

# * Write to file
# * ---------------------------------------------------------------------------
with open(output_json_path, 'w') as json_file:
    json.dump(output_json, json_file, indent=4)
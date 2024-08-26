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
output_json_name = "machine_gun_config_" + time.strftime("%Y%m%d_%H%M%S") + ".json"
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

udp_receive_timeout = 3

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
socket_udp.settimeout(udp_receive_timeout)

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
    pedestal_calib = json.load(json_file)
    _noinv_vref_list = pedestal_calib["noinv_vref_list"]
    _inv_vref_list = pedestal_calib["inv_vref_list"]
    trim_dac_values = pedestal_calib["chn_trim_settings"]

if len(_noinv_vref_list) == 0 or len(_inv_vref_list) == 0:
    print("Error: No pedestal calibration data")
    exit()

# * I2C register settings
# * ---------------------------------------------------------------------------
i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

top_reg_runLR = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
top_reg_offLR = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]

default_channel_wise = reg_settings.get_default_reg_content('registers_channel_wise')

default_ref_content = reg_settings.get_default_reg_content('registers_reference_voltage')

default_digital_content = reg_settings.get_default_reg_content('registers_digital_half')

output_json["i2c"] = {}
output_json["i2c"]["top_reg_runLR"] = top_reg_runLR
output_json["i2c"]["top_reg_offLR"] = top_reg_offLR

# * Parameters
# * ---------------------------------------------------------------------------
total_asic                  = 2
fpga_address                = 0x00
machine_gun_val             = 0
gen_fcmd_internal_injection = 0b00101101
gen_fcmd_L1A                = 0b01001011
gen_pre_inverval_value      = 20
gen_nr_cycle                = 10
gen_interval_value          = 20
internal_12b_dac_value      = 0x0FFF
target_chns = [30, 31, 32, 33, 34]
L1_offset   = 0x08
gen_pre_inverval_scan_range = range(0, 40)

i2c_setting_verbose = False
measurement_verbose = False

output_json["options"] = {}
output_json["options"]["total_asic"]        = total_asic
output_json["options"]["fpga_address"]      = fpga_address

default_reference_voltage = reg_settings.get_default_reg_content('registers_reference_voltage')


# * Get and print the status of the device
# * ---------------------------------------------------------------------------
data_packet = packetlib.pack_data_req_status(0xA0, 0x00)
socket_udp.sendto(data_packet, (h2gcroc_ip, h2gcroc_port))
received_data, addr = socket_udp.recvfrom(1024)
unpacked_data = packetlib.unpack_data_rpy_status(received_data)
if unpacked_data is not None:
    output_json["status"] = unpacked_data

# * Set up internal injection
# * ---------------------------------------------------------------------------
for _chn in range(2*76):
        _sub_addr = packetlib.uni_chn_to_subblock_list[_chn % 76]
        _half_num = _chn // 38
        _asic_num = _chn // 76
        
        # copy the default content
        _chn_content =default_channel_wise.copy()
        _chn_content[3] = (trim_dac_values[_chn] << 2) & 0xFC

        if target_chns.count(_chn) > 0:
            _chn_content[4] = 0x04

        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=False):
            if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic_num, fpga_addr = fpga_address, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=False):
                print('\033[33m' + "Warning: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')
            else:
                print('\033[32m' + "Fixed: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')
# set up reference voltage
for _asic in range(2):
    _ref_content_half0 = default_ref_content.copy()
    _ref_content_half1 = default_ref_content.copy()
    _ref_content_half0[4] = _inv_vref_list[_asic*2] >> 2
    _ref_content_half1[4] = _inv_vref_list[_asic*2+1] >> 2
    _ref_content_half0[5] = _noinv_vref_list[_asic*2] >> 2
    _ref_content_half1[5] = _noinv_vref_list[_asic*2+1] >> 2
    _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((_inv_vref_list[_asic*2] & 0x03) << 2) | (_noinv_vref_list[_asic*2] & 0x03)
    _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((_inv_vref_list[_asic*2+1] & 0x03) << 2) | (_noinv_vref_list[_asic*2+1] & 0x03)
    _ref_content_half0[7] = 0x40 | internal_12b_dac_value >> 8
    _ref_content_half0[6] = internal_12b_dac_value & 0xFF  
    _ref_content_half1[7] = 0x40 | internal_12b_dac_value >> 8
    _ref_content_half1[6] = internal_12b_dac_value & 0xFF
    _ref_content_half0[10]=0x40
    _ref_content_half1[10]=0x40
    # print("reference i2c: ", _ref_content_half0, _ref_content_half1)
    if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=False):
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=False):
            print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
        else:
            print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

    if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=False):
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=False):
            print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
        else:
            print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

# * Try machine gun
# * ---------------------------------------------------------------------------
val0_chn_3_matrix = []
gen_pre_inverval_values = []
sub_addr = packetlib.subblock_address_dict["Reference_Voltage_1"]
subaddr_10_3 = (sub_addr >> 3) & 0xFF
subaddr_2_0 = sub_addr & 0x07
read_req_packet = packetlib.pack_data_req_i2c_read(0xA1, fpga_address, 0x01, 32, subaddr_10_3, subaddr_2_0, 0x00)
socket_udp.sendto(read_req_packet, (h2gcroc_ip, h2gcroc_port))
received_data, addr = socket_udp.recvfrom(1024)

for asic in range(2):
    packetlib.read_save_all_i2c('i2c_debug_info_'+ str(asic) + '.txt', socket_udp, h2gcroc_ip, h2gcroc_port, asic, fpga_address)

for gen_pre_inverval_value in tqdm(gen_pre_inverval_scan_range):
    for asic in range(2):
        if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, asic, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_preimp_en=1, gen_pre_interval = gen_pre_inverval_value, gen_nr_of_cycle=gen_nr_cycle, gen_pre_fcmd=gen_fcmd_internal_injection,gen_fcmd=gen_fcmd_L1A,gen_interval=gen_interval_value, daq_push_fcmd=75, machine_gun=machine_gun_val,verbose=measurement_verbose):
            if measurement_verbose:
                print('\033[33m' + "Warning: Generator parameters not match" + '\033[0m')

    for asic in range(2):
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, verbose=measurement_verbose):
            if measurement_verbose:
                print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(asic) + '\033[0m')

    # ! Request data for several times
    # ! ---------------------------------------------------------------------------
    if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=1, daq_start_stop=0xFF, verbose=False):
        print('\033[33m' + "Warning in sending DAQ Push" + '\033[0m')

    expected_half_packet_num = gen_nr_cycle * (machine_gun_val+1) * 4
    expected_event_num = gen_nr_cycle * (machine_gun_val+1)
    extracted_payloads = []
    event_fragment_pool = []
    current_half_packet_num = 0
    current_event_num = 0

    header_byte_array   = bytearray()
    all_chn_value_0_arrary = np.zeros((expected_event_num, 152))
    all_chn_value_1_arrary = np.zeros((expected_event_num, 152))
    all_chn_value_2_arrary = np.zeros((expected_event_num, 152))
    

    # hammingCodePass = False
    # retry_attempt = 0
    # while not hammingCodePass and retry_attempt < hammingcode_max:
    #     retry_attempt += 1

    while True:
        try:
            data_packet, rec_addr   = socket_udp.recvfrom(8192)
            extracted_payloads += packetlib.extract_raw_payloads(data_packet)
            if len(extracted_payloads) >= 5:
                while len(extracted_payloads) >= 5:
                    candidate_packet_lines = extracted_payloads[:5]
                    is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
                    if is_packet_good:
                        event_fragment_pool.append(event_fragment)
                        current_half_packet_num += 1
                        extracted_payloads = extracted_payloads[5:]
                    else:
                        print('\033[33m' + "Warning: Event fragment is not good" + '\033[0m')
                        extracted_payloads = extracted_payloads[1:]
            if len(event_fragment_pool) >= 4:
                event_fragment_pool = sorted(event_fragment_pool, key=lambda x: x[0][3:7])
                # print("Sorted event fragments: " + str(len(event_fragment_pool)))
                # for i in range(len(event_fragment_pool)):
                #     print(event_fragment_pool[i][0][7])
                while len(event_fragment_pool) >= 4:
                    # check if the 4 consecutive packets have same byte 4-7
                    timestamp0 = event_fragment_pool[0][0][4] << 24 | event_fragment_pool[0][0][5] << 16 | event_fragment_pool[0][0][6] << 8 | event_fragment_pool[0][0][7]
                    timestamp1 = event_fragment_pool[1][0][4] << 24 | event_fragment_pool[1][0][5] << 16 | event_fragment_pool[1][0][6] << 8 | event_fragment_pool[1][0][7]
                    timestamp2 = event_fragment_pool[2][0][4] << 24 | event_fragment_pool[2][0][5] << 16 | event_fragment_pool[2][0][6] << 8 | event_fragment_pool[2][0][7]
                    timestamp3 = event_fragment_pool[3][0][4] << 24 | event_fragment_pool[3][0][5] << 16 | event_fragment_pool[3][0][6] << 8 | event_fragment_pool[3][0][7]
                    if timestamp0 == timestamp1 and timestamp0 == timestamp2 and timestamp0 == timestamp3:
                        # print("good event fragment")
                        for i in range(4):
                            extracted_data = packetlib.assemble_data_from_40bytes(event_fragment_pool[i], verbose=False)
                            extracted_values = packetlib.extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
                            uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
                            for j in range(len(extracted_values["_extracted_values"])):
                                all_chn_value_0_arrary[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
                                all_chn_value_1_arrary[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
                                all_chn_value_2_arrary[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
                        # delete the fragments in the pool
                        event_fragment_pool = event_fragment_pool[4:]
                        current_event_num += 1
                    else:
                        # print("bad event fragment")
                        event_fragment_pool = event_fragment_pool[1:]
            #print('current_half_packet_num: ', current_half_packet_num, ' expected_half_packet_num: ', expected_half_packet_num)
            if current_half_packet_num >= expected_half_packet_num:
                break
        except Exception as e:
            if True:
                print('\033[33m' + "Warning: Exception in receiving data" + '\033[0m')
                print(e)
            break

    for asic in range(2):
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, verbose=measurement_verbose):
            if measurement_verbose:
                print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(asic) + '\033[0m')

    if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
        print('\033[33m' + "Warning in sending DAQ Push" + '\033[0m')

    # * draw the data with a 2-D histogram
    # # * ---------------------------------------------------------------------------
    # xbins = np.linspace(0, 38, 38)
    # ybins = np.linspace(0, 512, 128)

    # # process all_chn_value_0_arrary, all_chn_value_1_arrary, 
    # # all_chn_value_2_arrary to x and y
    # val_0_x_vals = []
    # val_0_y_vals = []
    # val_1_x_vals = []
    # val_1_y_vals = []
    # val_2_x_vals = []
    # val_2_y_vals = []

    # for i in range(expected_event_num):
    #     for j in range(152):
    #         val_0_x_vals.append(j)
    #         val_0_y_vals.append(all_chn_value_0_arrary[i][j])
    #         val_1_x_vals.append(j)
    #         val_1_y_vals.append(all_chn_value_1_arrary[i][j])
    #         val_2_x_vals.append(j)
    #         val_2_y_vals.append(all_chn_value_2_arrary[i][j])

    # fig, axs = plt.subplots(3, 1, figsize=(10, 12), dpi=300)
    # axs[0].hist2d(val_0_x_vals, val_0_y_vals, bins=(xbins,ybins))
    # axs[0].set_xlabel('Channel')
    # axs[0].set_ylabel('ADC Value')
    # axs[0].annotate('Gen Pre Interval: ' + str(gen_pre_inverval_value), xy=(0.02, 0.85), xycoords='axes fraction', ha='left', va='center')
    # axs[1].hist2d(val_1_x_vals, val_1_y_vals, bins=(xbins,ybins))
    # axs[1].set_xlabel('Channel')
    # axs[1].set_ylabel('ADC Value')
    # axs[2].hist2d(val_2_x_vals, val_2_y_vals, bins=(xbins,ybins))
    # axs[2].set_xlabel('Channel')
    # axs[2].set_ylabel('ADC Value')

    # plt.tight_layout()
    # plt.savefig('test.png')

    # # get all data for chn 3
    # val_0_chn_3 = []
    # for i in range(expected_event_num):
    #     val_0_chn_3.append(all_chn_value_0_arrary[i][31])

    # val0_chn_3_matrix.append(val_0_chn_3)
    # gen_pre_inverval_values.append(gen_pre_inverval_value)

fig2, ax2 = plt.subplots(dpi=300)
xvalues = []
yvalues = []
for i in range(len(val0_chn_3_matrix)):
    for j in range(len(val0_chn_3_matrix[i])):
        xvalues.append(gen_pre_inverval_values[i])
        yvalues.append(val0_chn_3_matrix[i][j])
ax2.hist2d(xvalues, yvalues, bins=(np.linspace(0,40,40), np.linspace(0,512,128)))
ax2.set_xlabel('Gen Pre Interval')
ax2.set_ylabel('ADC Value')
plt.savefig('test2.png')
    


# * Write to file
# * ---------------------------------------------------------------------------
with open(output_json_path, 'w') as json_file:
    json.dump(output_json, json_file, indent=4)


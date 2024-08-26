import packetlib
import socket
import numpy as np
import time
import json
import os

from tqdm import tqdm
from itertools import groupby
import matplotlib.pyplot as plt

# * UDP Settings
# * ---------------------------------------------------------------------------
output_file_path = "dump"
output_json_name = "pede_calib_config_" + time.strftime("%Y%m%d_%H%M%S") + ".json"
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

def calculate_segment_stats(data, start, end, channel_not_used):
    total = 0
    valid_chn_cnt = 0
    values = []  # List to store valid values for std calculation

    for i in range(start, end):
        if i not in channel_not_used:
            total += data[i]
            values.append(data[i])
            valid_chn_cnt += 1
    
    average = total / valid_chn_cnt if valid_chn_cnt > 0 else float('nan')
    std_dev = np.std(values) if valid_chn_cnt > 0 else float('nan')  # Calculate standard deviation using numpy

    return average, std_dev

# * I2C register settings
# * ---------------------------------------------------------------------------
i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

top_reg_runLR = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
top_reg_offLR = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]

default_global_analog   = reg_settings.get_default_reg_content('registers_global_analog')

output_json["i2c"] = {}
output_json["i2c"]["top_reg_runLR"] = top_reg_runLR
output_json["i2c"]["top_reg_offLR"] = top_reg_offLR

# * Parameters
# * ---------------------------------------------------------------------------
total_asic          = 2
fpga_address        = 0x00
channel_not_used    =[0, 19, 38, 57, 76, 95, 114, 133]
gen_nr_cycle        = 1
gen_interval_value  = 100
hammingcode_max     = 100
half_target_offset  = 2
chn_fine_tunning_threshold = 1
ref_fine_tunning_threshold = 2
trim_scan_verbose   = False
global_scan_verbose = False
global_pedestal_target = 120
chn_tunning_step = 1
global_tunning_step = 5
chn_trim_values_corse = range(0, 64, 4)
chn_trim_values_fine  = range(0, 64, 2)
global_inv_vref_range = range(200, 1000, 10)

channel_ranges = [(0, 38), (38, 76), (76, 114), (114, 152)]
chn_trim_settings = []
for _chn in range(152):
    chn_trim_settings.append(0)

i2c_setting_verbose = False

inv_vref_list   = [300,400,400,300]
noinv_vref_list = [500,400,400,500]


output_json["options"] = {}
output_json["options"]["total_asic"]        = total_asic
output_json["options"]["fpga_address"]      = fpga_address
output_json["options"]["channel_not_used"]  = channel_not_used
output_json["options"]["gen_nr_cycle"]      = gen_nr_cycle
output_json["options"]["gen_interval_value"]= gen_interval_value
output_json["options"]["hammingcode_max"]   = hammingcode_max
output_json["options"]["half_target_offset"]= half_target_offset
output_json["options"]["chn_fine_tunning_threshold"] = chn_fine_tunning_threshold
output_json["options"]["ref_fine_tunning_threshold"] = ref_fine_tunning_threshold
output_json["options"]["trim_scan_verbose"] = trim_scan_verbose
output_json["options"]["global_pedestal_target"] = global_pedestal_target
output_json["options"]["chn_tunning_step"] = chn_tunning_step
output_json["options"]["global_tunning_step"] = global_tunning_step

# * Get and print the status of the device
# * ---------------------------------------------------------------------------
data_packet = packetlib.pack_data_req_status(0xA0, 0x00)
socket_udp.sendto(data_packet, (h2gcroc_ip, h2gcroc_port))
received_data, addr = socket_udp.recvfrom(2048)
unpacked_data = packetlib.unpack_data_rpy_status(received_data)
if unpacked_data is not None:
    output_json["status"] = unpacked_data

target_value_array = [0,0,0,0]
_meansure_verbose = 1
if trim_scan_verbose:
    _meansure_verbose = 1

interested_value_averages = []
interested_value_trims = []

for _asic in range(2):
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

print('\033[34m' + 'Channel Trim Scanning ...' + '\033[0m')
for chn_trim_value in tqdm(chn_trim_values_corse):
    if trim_scan_verbose:
        print('\033[34m' + 'Channel Trim Value: ' + str(chn_trim_value) + '\033[0m')
    # have 312 zeros
    _trim_inv_list = []
    for i in range(2*76):
        _trim_inv_list.append(chn_trim_value)

    chn_i2c_content = reg_settings.get_default_reg_content('registers_channel_wise')
    # chn_i2c_content[4] = 0x04
    chn_i2c_content[14] = 0xC0
    ref_i2c_content = reg_settings.get_default_reg_content('registers_reference_voltage')

    hammingCodePass = False
    retry_attempt = 0
    while not hammingCodePass and retry_attempt < hammingcode_max:
        retry_attempt += 1
        # print(f'Attempt {retry_attempt}')
        measurement_data = packetlib.fast_set_and_measure_pedestal(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, _trim_inv_list, inv_vref_list, noinv_vref_list, channel_not_used, chn_i2c_content, ref_i2c_content, top_reg_runLR, top_reg_offLR, gen_nr_cycle, gen_interval_value, _verbose=_meansure_verbose)
        # print("Finished")
        daqH_array = measurement_data["daqh_array"]
        hammingCodePass = True
        for i in range(len(daqH_array)):
            hammingcode = [packetlib.DaqH_get_H1(daqH_array[i]), packetlib.DaqH_get_H2(daqH_array[i]), packetlib.DaqH_get_H3(daqH_array[i])]
            hammingCodePass = not any(code == 1 for code in hammingcode)  # Check if any code is 1
            hammingcodestr = ''.join('\033[31m1\033[0m' if code == 1 else '0' for code in hammingcode)
            if not hammingCodePass:
                print(f'Hamming Code (half {i%4}): {hammingcodestr}')
    if not hammingCodePass:
        print('\033[31m' + 'Hamming Code Error after ' + str(hammingcode_max) + ' attempts' + '\033[0m')

    all_chn_average_0   = measurement_data["all_chn_average_0"]
    all_chn_error_0     = measurement_data["all_chn_error_0"]
    all_chn_average_1   = measurement_data["all_chn_average_1"]
    all_chn_error_1     = measurement_data["all_chn_error_1"]
    all_chn_average_2   = measurement_data["all_chn_average_2"]
    all_chn_error_2     = measurement_data["all_chn_error_2"]

    interested_value_averages.append(all_chn_average_0)
    interested_value_trims.append(chn_trim_value)

half_average = [0,0,0,0]
half_valid_chn_cnt = [0,0,0,0]
for _chn in range(152):
    if channel_not_used.count(_chn) > 0:
        continue
    half_index = _chn // 38
    half_average[half_index] += interested_value_averages[0][_chn]
    half_valid_chn_cnt[half_index] += 1

for i in range(4):
    half_average[i] /= half_valid_chn_cnt[i]

# detect dead channels
for _chn in range(152):
    if channel_not_used.count(_chn) > 0:
        continue
    _all_trim_values = []
    for _avg in interested_value_averages:
        _all_trim_values.append(_avg[_chn])
    _std = np.std(_all_trim_values)
    _average_avg = np.average(_all_trim_values)
    if _std < 2:
        channel_not_used.append(_chn)
        print('\033[31m' + 'Dead Channel: ' + str(_chn) + '\033[0m')
    elif _average_avg > half_average[_chn // 38] + 100:
        channel_not_used.append(_chn)
        print('\033[31m' + 'Dead Channel: ' + str(_chn) + '\033[0m')


# get the max value of each half
half_ranges = [(0, 38), (38, 76), (76, 114), (114, 152)]
for _chn in range(152):
    if channel_not_used.count(_chn) > 0:
        continue
    half_index = _chn // 38
    if interested_value_averages[0][_chn] > target_value_array[half_index]:
        target_value_array[half_index] = interested_value_averages[0][_chn][0]

for target_index in range(4):
    target_value_array[target_index] += half_target_offset

print('target values:')
print(target_value_array)

# find the best trim value
for _chn in range(152):
    if channel_not_used.count(_chn) > 0:
        continue
    _interested_values = []
    for _avg in interested_value_averages:
        _interested_values.append(_avg[_chn])
    # print(f'Channel {_chn} - {_interested_values}')
    _half_index = _chn // 38
    _dist_list = []
    for _val in _interested_values:
        _dist_list.append(abs(_val[0] - target_value_array[_half_index]))
    _min_dist = min(_dist_list)
    _min_dist_index = _dist_list.index(_min_dist)
    chn_trim_settings[_chn] = interested_value_trims[_min_dist_index]

print('channel trim settings:')
print(chn_trim_settings)

hammingCodePass = False
retry_attempt = 0
while not hammingCodePass and retry_attempt < hammingcode_max:
    retry_attempt += 1
    measurement_data = packetlib.set_and_measure_pedestal(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, chn_trim_settings, inv_vref_list, noinv_vref_list, channel_not_used, chn_i2c_content, ref_i2c_content, top_reg_runLR, top_reg_offLR, gen_nr_cycle, gen_interval_value, _verbose=_meansure_verbose)
    daqH_array = measurement_data["daqh_array"]
    hammingCodePass = True
    for i in range(len(daqH_array)):
        hammingcode = [packetlib.DaqH_get_H1(daqH_array[i]), packetlib.DaqH_get_H2(daqH_array[i]), packetlib.DaqH_get_H3(daqH_array[i])]
        hammingCodePass = not any(code == 1 for code in hammingcode)  # Check if any code is 1
        hammingcodestr = ''.join('\033[31m1\033[0m' if code == 1 else '0' for code in hammingcode)
        if not hammingCodePass:
            print(f'Hamming Code (half {i%4}): {hammingcodestr}')
if not hammingCodePass:
    print('\033[31m' + 'Hamming Code Error after ' + str(hammingcode_max) + ' attempts' + '\033[0m')

all_chn_average_0   = measurement_data["all_chn_average_0"]
all_chn_error_0     = measurement_data["all_chn_error_0"]
all_chn_average_1   = measurement_data["all_chn_average_1"]
all_chn_error_1     = measurement_data["all_chn_error_1"]
all_chn_average_2   = measurement_data["all_chn_average_2"]
all_chn_error_2     = measurement_data["all_chn_error_2"]

interested_inv_value_averages = []
interested_inv_values = []
print('\033[34m' + 'Global Inv Scanning ...' + '\033[0m')
for global_inv_vref in tqdm(global_inv_vref_range):
    interested_inv_values.append(global_inv_vref)
    for _half in range(4):
        inv_vref_list[_half] = global_inv_vref
    hammingCodePass = False
    retry_attempt = 0
    while not hammingCodePass and retry_attempt < hammingcode_max:
        retry_attempt += 1
        measurement_data = packetlib.ref_set_and_measure_pedestal(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, chn_trim_settings, inv_vref_list, noinv_vref_list, channel_not_used, chn_i2c_content, ref_i2c_content, top_reg_runLR, top_reg_offLR, gen_nr_cycle, gen_interval_value, _verbose=_meansure_verbose)
        daqH_array = measurement_data["daqh_array"]
        hammingCodePass = True
        for i in range(len(daqH_array)):
            hammingcode = [packetlib.DaqH_get_H1(daqH_array[i]), packetlib.DaqH_get_H2(daqH_array[i]), packetlib.DaqH_get_H3(daqH_array[i])]
            hammingCodePass = not any(code == 1 for code in hammingcode)
            hammingcodestr = ''.join('\033[31m1\033[0m' if code == 1 else '0' for code in hammingcode)
            if not hammingCodePass:
                print(f'Hamming Code (half {i%4}): {hammingcodestr}')
    if not hammingCodePass:
        print('\033[31m' + 'Hamming Code Error after ' + str(hammingcode_max) + ' attempts' + '\033[0m')

    all_chn_average_0   = measurement_data["all_chn_average_0"]
    all_chn_error_0     = measurement_data["all_chn_error_0"]
    all_chn_average_1   = measurement_data["all_chn_average_1"]
    all_chn_error_1     = measurement_data["all_chn_error_1"]
    all_chn_average_2   = measurement_data["all_chn_average_2"]
    all_chn_error_2     = measurement_data["all_chn_error_2"]

    half_valid_chn_cnt = [0,0,0,0]
    half_average = [0,0,0,0]
    for _chn in range(152):
        if channel_not_used.count(_chn) > 0:
            continue
        half_index = _chn // 38
        half_average[half_index] += all_chn_average_0[_chn]
        half_valid_chn_cnt[half_index] += 1
    for i in range(4):
        half_average[i] /= half_valid_chn_cnt[i]

    interested_inv_value_averages.append(half_average)

# find the best global inv value
for _half in range(4):
    _interested_values = []
    for _avg in interested_inv_value_averages:
        _interested_values.append(_avg[_half][0])
    # print(f'Half {_half} - {_interested_values}')
    _dist_list = []
    for _val in _interested_values:
        _dist_list.append(abs(_val - global_pedestal_target))
    _min_dist = min(_dist_list)
    _min_dist_index = _dist_list.index(_min_dist)
    inv_vref_list[_half] = interested_inv_values[_min_dist_index]

print('global inv values:')
print(inv_vref_list)

hammingCodePass = False
retry_attempt = 0
while not hammingCodePass and retry_attempt < hammingcode_max:
    retry_attempt += 1
    measurement_data = packetlib.set_and_measure_pedestal(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, chn_trim_settings, inv_vref_list, noinv_vref_list, channel_not_used, chn_i2c_content, ref_i2c_content, top_reg_runLR, top_reg_offLR, gen_nr_cycle, gen_interval_value, _verbose=_meansure_verbose)
    daqH_array = measurement_data["daqh_array"]
    hammingCodePass = True
    for i in range(len(daqH_array)):
        hammingcode = [packetlib.DaqH_get_H1(daqH_array[i]), packetlib.DaqH_get_H2(daqH_array[i]), packetlib.DaqH_get_H3(daqH_array[i])]
        hammingCodePass = not any(code == 1 for code in hammingcode)
        hammingcodestr = ''.join('\033[31m1\033[0m' if code == 1 else '0' for code in hammingcode)
        if not hammingCodePass:
            print(f'Hamming Code (half {i%4}): {hammingcodestr}')
if not hammingCodePass:
    print('\033[31m' + 'Hamming Code Error after ' + str(hammingcode_max) + ' attempts' + '\033[0m')

all_chn_average_0   = measurement_data["all_chn_average_0"]
all_chn_error_0     = measurement_data["all_chn_error_0"]
all_chn_average_1   = measurement_data["all_chn_average_1"]
all_chn_error_1     = measurement_data["all_chn_error_1"]
all_chn_average_2   = measurement_data["all_chn_average_2"]
all_chn_error_2     = measurement_data["all_chn_error_2"]

interested_value_averages = []
interested_value_trims = []

for chn_trim_value in tqdm(chn_trim_values_fine):
    if trim_scan_verbose:
        print('\033[34m' + 'Channel Trim Value: ' + str(chn_trim_value) + '\033[0m')
    # have 312 zeros
    _trim_inv_list = []
    for i in range(2*76):
        _trim_inv_list.append(chn_trim_value)

    hammingCodePass = False
    retry_attempt = 0
    while not hammingCodePass and retry_attempt < hammingcode_max:
        retry_attempt += 1
        measurement_data = packetlib.fast_set_and_measure_pedestal(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, _trim_inv_list, inv_vref_list, noinv_vref_list, channel_not_used, chn_i2c_content, ref_i2c_content, top_reg_runLR, top_reg_offLR, gen_nr_cycle, gen_interval_value, _verbose=_meansure_verbose)
        daqH_array = measurement_data["daqh_array"]
        hammingCodePass = True
        for i in range(len(daqH_array)):
            hammingcode = [packetlib.DaqH_get_H1(daqH_array[i]), packetlib.DaqH_get_H2(daqH_array[i]), packetlib.DaqH_get_H3(daqH_array[i])]
            hammingCodePass = not any(code == 1 for code in hammingcode)  # Check if any code is 1
            hammingcodestr = ''.join('\033[31m1\033[0m' if code == 1 else '0' for code in hammingcode)
            if not hammingCodePass:
                print(f'Hamming Code (half {i%4}): {hammingcodestr}')
    if not hammingCodePass:
        print('\033[31m' + 'Hamming Code Error after ' + str(hammingcode_max) + ' attempts' + '\033[0m')

    all_chn_average_0   = measurement_data["all_chn_average_0"]
    all_chn_error_0     = measurement_data["all_chn_error_0"]
    all_chn_average_1   = measurement_data["all_chn_average_1"]
    all_chn_error_1     = measurement_data["all_chn_error_1"]
    all_chn_average_2   = measurement_data["all_chn_average_2"]
    all_chn_error_2     = measurement_data["all_chn_error_2"]

    interested_value_averages.append(all_chn_average_0)
    interested_value_trims.append(chn_trim_value)

# find the best trim value for global pedestal
for _chn in range(152):
    if channel_not_used.count(_chn) > 0:
        continue
    _interested_values = []
    for _avg in interested_value_averages:
        _interested_values.append(_avg[_chn])
    _half_index = _chn // 38
    _dist_list = []
    for _val in _interested_values:
        _dist_list.append(abs(_val[0] - global_pedestal_target))
    _min_dist = min(_dist_list)
    _min_dist_index = _dist_list.index(_min_dist)
    chn_trim_settings[_chn] = interested_value_trims[_min_dist_index]

print('channel trim settings:')
print(chn_trim_settings)

hammingCodePass = False
retry_attempt = 0
while not hammingCodePass and retry_attempt < hammingcode_max:
    retry_attempt += 1
    measurement_data = packetlib.set_and_measure_pedestal(socket_udp, h2gcroc_ip, h2gcroc_port, fpga_address, chn_trim_settings, inv_vref_list, noinv_vref_list, channel_not_used, chn_i2c_content, ref_i2c_content, top_reg_runLR, top_reg_offLR, gen_nr_cycle, gen_interval_value, _verbose=_meansure_verbose)
    daqH_array = measurement_data["daqh_array"]
    hammingCodePass = True
    for i in range(len(daqH_array)):
        hammingcode = [packetlib.DaqH_get_H1(daqH_array[i]), packetlib.DaqH_get_H2(daqH_array[i]), packetlib.DaqH_get_H3(daqH_array[i])]
        hammingCodePass = not any(code == 1 for code in hammingcode)
        hammingcodestr = ''.join('\033[31m1\033[0m' if code == 1 else '0' for code in hammingcode)
        if not hammingCodePass:
            print(f'Hamming Code (half {i%4}): {hammingcodestr}')
if not hammingCodePass:
    print('\033[31m' + 'Hamming Code Error after ' + str(hammingcode_max) + ' attempts' + '\033[0m')

all_chn_average_0   = measurement_data["all_chn_average_0"]
all_chn_error_0     = measurement_data["all_chn_error_0"]
all_chn_average_1   = measurement_data["all_chn_average_1"]
all_chn_error_1     = measurement_data["all_chn_error_1"]
all_chn_average_2   = measurement_data["all_chn_average_2"]
all_chn_error_2     = measurement_data["all_chn_error_2"]


# * Plot
# * ---------------------------------------------------------------------------
fig0_0, ax0_0 = plt.subplots(dpi=300)
ax0_0.errorbar(range(152), all_chn_average_0.flatten(), yerr=all_chn_error_0.flatten(), fmt='o', label='Val 0', color='b', markersize=2)
ax0_0.set_xlabel('Channel')
ax0_0.set_xlim([0, 152])
ax0_0.set_ylim([0, 1023])
ax0_0.vlines(x=[0, 19, 38, 57, 76, 95, 114, 133, 152], ymin=0, ymax=1023, colors='k', linestyles='dashed', alpha=0.5)
ax0_0.hlines(y=[0, 511, 1023], xmin=0, xmax=152, colors='k', linestyles='dashed', alpha=0.5)
ax0_0.hlines(y=target_value_array[0], xmin=0, xmax=38, colors='b', linestyles='dashed', alpha=0.5, label='Half Calib Target')
ax0_0.hlines(y=target_value_array[1], xmin=38, xmax=76, colors='b', linestyles='dashed', alpha=0.5)
ax0_0.hlines(y=target_value_array[2], xmin=76, xmax=114, colors='b', linestyles='dashed', alpha=0.5)
ax0_0.hlines(y=target_value_array[3], xmin=114, xmax=152, colors='b', linestyles='dashed', alpha=0.5)
ax0_0.hlines(y=global_pedestal_target, xmin=0, xmax=152, colors='r', linestyles='dashed', alpha=0.5, label='Global Calib Target')

ax0_0.legend()
ax0_0.annotate('Pedestal Measurement', xy=(0.02, 0.95), xycoords='axes fraction', fontsize=14, color='k', ha='left', va='center', weight='bold')
ax0_0.annotate('Average of ' + str(gen_nr_cycle) + ' measurements', xy=(0.02, 0.9), xycoords='axes fraction', fontsize=12, color='k', ha='left', va='center')
ax0_0.annotate(time.strftime("%Y-%m-%d"), xy=(0.02, 0.85), xycoords='axes fraction', fontsize=12, color='k', ha='left', va='center')
fig0_0.tight_layout()
fig0_0.savefig(os.path.join(output_file_path, "pede_measurement_v0_" + time.strftime("%Y%m%d_%H%M%S") + ".png"))

fig0_1, ax0_1 = plt.subplots(dpi=300)
ax0_1.errorbar(range(152), all_chn_average_1.flatten(), yerr=all_chn_error_1.flatten(), fmt='o', label='Val 1', color='g', markersize=2)
ax0_1.set_xlabel('Channel')
ax0_1.set_xlim([0, 152])
ax0_1.set_ylim([0, 1023])
ax0_1.vlines(x=[0, 19, 38, 57, 76, 95, 114, 133, 152], ymin=0, ymax=1023, colors='k', linestyles='dashed', alpha=0.5)
ax0_1.hlines(y=[0, 511, 1023], xmin=0, xmax=152, colors='k', linestyles='dashed', alpha=0.5)
ax0_1.legend()
ax0_1.annotate('Pedestal Measurement', xy=(0.02, 0.95), xycoords='axes fraction', fontsize=14, color='k', ha='left', va='center', weight='bold')
ax0_1.annotate('Average of ' + str(gen_nr_cycle) + ' measurements', xy=(0.02, 0.9), xycoords='axes fraction', fontsize=12, color='k', ha='left', va='center')
ax0_1.annotate(time.strftime("%Y-%m-%d"), xy=(0.02, 0.85), xycoords='axes fraction', fontsize=12, color='k', ha='left', va='center')
fig0_1.tight_layout()
fig0_1.savefig(os.path.join(output_file_path, "pede_measurement_v1_" + time.strftime("%Y%m%d_%H%M%S") + ".png"))

fig0_2, ax0_2 = plt.subplots(dpi=300)
ax0_2.errorbar(range(152), all_chn_average_2.flatten(), yerr=all_chn_error_2.flatten(), fmt='o', label='Val 2', color='r', markersize=2)
ax0_2.set_xlabel('Channel')
ax0_2.set_xlim([0, 152])
ax0_2.set_ylim([0, 1023])
ax0_2.vlines(x=[0, 19, 38, 57, 76, 95, 114, 133, 152], ymin=0, ymax=1023, colors='k', linestyles='dashed', alpha=0.5)
ax0_2.hlines(y=[0, 511, 1023], xmin=0, xmax=152, colors='k', linestyles='dashed', alpha=0.5)
ax0_2.legend()
ax0_2.annotate('Pedestal Measurement', xy=(0.02, 0.95), xycoords='axes fraction', fontsize=14, color='k', ha='left', va='center', weight='bold')
ax0_2.annotate('Average of ' + str(gen_nr_cycle) + ' measurements', xy=(0.02, 0.9), xycoords='axes fraction', fontsize=12, color='k', ha='left', va='center')
ax0_2.annotate(time.strftime("%Y-%m-%d"), xy=(0.02, 0.85), xycoords='axes fraction', fontsize=12, color='k', ha='left', va='center')
fig0_2.tight_layout()
fig0_2.savefig(os.path.join(output_file_path, "pede_measurement_v2_" + time.strftime("%Y%m%d_%H%M%S") + ".png"))

# * Write to file
# * ---------------------------------------------------------------------------
output_json["target_values"] = target_value_array

output_json["noinv_vref_list"] = noinv_vref_list
output_json["inv_vref_list"] = inv_vref_list
output_json["chn_trim_settings"] = chn_trim_settings
output_json["channel_not_used"] = channel_not_used

with open(output_json_path, 'w') as json_file:
    json.dump(output_json, json_file, indent=4)
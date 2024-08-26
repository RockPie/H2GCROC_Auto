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
import matplotlib as mpl

# * --- Set up script information -------------------------------------
script_id_str       = '607_PhaseScan'
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

# * --- Set up argument parser -----------------------------------------
default_output_file_name = script_id_str + time.strftime("_%Y%m%d_%H%M%S", time.localtime()) + '.png'
parser = argparse.ArgumentParser(description='DAQ script for data acquisition')
parser.add_argument('-n', '--num', type=int, help='Number of events to process')
parser.add_argument('-a', '--show_A', action='store_true', help='Show A side data')
parser.add_argument('-b', '--show_B', action='store_true', help='Show B side data')

args = parser.parse_args()

showing_A = True
showing_B = False

if not showing_A and not showing_B:
    logger.error('No board specified')

# * --- Read the input file -------------------------------------------
input_file_folder = 'data'
input_file_name_prefix = 'Phase'
input_file_name_suffix = '.txt'
input_file_names = [f for f in os.listdir(input_file_folder) if f.startswith(input_file_name_prefix) and f.endswith(input_file_name_suffix)]

logger.info(f'Found input files: {input_file_names}')

phase_array = []
machinegun_file_list = []
val0_file_list = []
val1_file_list = []

for _file in input_file_names:
    # file name like: Phase13.txt
    _phase_values = _file.split('.')[0].split('Phase')[1]
    _phase_values = int(_phase_values)
    _phase_values = _phase_values - 8
    if _phase_values < 0:
        _phase_values = _phase_values + 16
    phase_array.append(_phase_values)

    logger.info(f'Processing file {_file} with phase values {_phase_values}')

    _fragment_life = 100

    _file_path = os.path.join(input_file_folder, _file)
    with open(_file_path, 'r') as f:
        extracted_payloads_pool = []
        event_fragment_pool     = []
        fragment_life_dict      = {}

        current_event_num = 0
        expected_event_num = 100000 if args.num is None else args.num

        all_chn_value_0_array = np.zeros((expected_event_num, 152))
        all_chn_value_1_array = np.zeros((expected_event_num, 152))
        all_chn_value_2_array = np.zeros((expected_event_num, 152))
        hamming_code_array    = np.zeros((expected_event_num, 12))

        last_timestamp = 0
        timestamp_diff_pack = []
        machine_gun_counter_pack = []

        machine_gun_counter = 0
        timestamp_diff_threshold = 100

        for line in f:
            # if it starts with a #, it is a comment
            if line.startswith('#'):
                continue
            # if it is not a comment, it is a data line
            data = line.split()
            if not showing_A:
                if data[1] == '00':
                    continue
            if not showing_B:
                if data[1] == '01':
                    continue    
            bytearray_line = bytearray()
            for d in data:
                bytearray_line.append(int(d, 16))

            extracted_payloads_pool.append(bytearray_line)
            while len(extracted_payloads_pool) >= 5:
                candidate_packet_lines = extracted_payloads_pool[:5]
                is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
                if is_packet_good:
                    event_fragment_pool.append(event_fragment)
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
                    timestamp = int(id_str, 16)
                    timediff = timestamp - last_timestamp
                    if len(timestamp_diff_pack) == 0:
                        timestamp_diff_pack.append(100)
                    else:
                        timestamp_diff_pack.append(timediff)
                    if timediff < 0:
                        print(f"timestamp: {timestamp}, last_timestamp: {last_timestamp}, timediff: {timediff}")
                        timediff += 2**30
                    last_timestamp = timestamp
                    for _half in range(4):
                        extracted_data = packetlib.assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
                        extracted_values = packetlib.extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
                        
                        DaqH_info = extracted_values["_DaqH"]
                        # check if the DaqH is good
                        good_DaqH = (DaqH_info[0] >> 4) == 0x05 and (DaqH_info[-1] & 0x0F) == 0x05
                        if not good_DaqH:
                        # logger.warning(f'Bad DaqH: {DaqH_info}')
                            uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
                            for j in range(len(extracted_values["_extracted_values"])):
                                all_chn_value_0_array[current_event_num][j+uni_chn_base] = 0
                                all_chn_value_1_array[current_event_num][j+uni_chn_base] = 0
                                all_chn_value_2_array[current_event_num][j+uni_chn_base] = 0


                        else:
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
                    if timediff < timestamp_diff_threshold:
                        machine_gun_counter += 1
                    else:
                        machine_gun_counter = 0
                    machine_gun_counter_pack.append(machine_gun_counter)
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
            if current_event_num == expected_event_num:
                break;      

    if current_event_num < expected_event_num:
        logger.warning(f'Only {current_event_num} events are extracted')
        expected_event_num = current_event_num

    machinegun_file_list.append(machine_gun_counter_pack)
    val0_file_list.append(all_chn_value_0_array)
    val1_file_list.append(all_chn_value_1_array)

L1_scan_channel = 10

hist_1d_x = []
hist_1d_y = []

hist_tot = []

for _file_index in range(len(phase_array)):
    machine_gun_counter_pack = machinegun_file_list[_file_index]
    all_chn_value_0_array = val0_file_list[_file_index]
    all_chn_value_1_array = val1_file_list[_file_index]
    expected_event_num = len(machine_gun_counter_pack)
    _phase_val = phase_array[_file_index]
    logger.info(f'Processing phase value {_phase_val} with {_file_index} file index')
    for _event in range(expected_event_num):
        time_clk = machine_gun_counter_pack[_event] + _phase_val * 1.0 / 16.0
        time_real = time_clk * 25.0
        hist_1d_x.append(time_real)
        hist_1d_y.append(all_chn_value_0_array[_event][L1_scan_channel])
        if all_chn_value_1_array[_event][L1_scan_channel] > 0:
            hist_tot.append(machine_gun_counter_pack[_event] + _phase_val * 1.0 / 16.0)

fig, ax = plt.subplots(1, 1, figsize=(12, 6), dpi = 300)
machine_gun_min = min(machine_gun_counter_pack)
machine_gun_max = 10
machine_gun_bins = machine_gun_max - machine_gun_min
ax.hist2d(hist_1d_x, hist_1d_y, bins=(10*16, 256), range=((0, 250), (0, 1024)), cmap=plt.cm.jet, norm=mpl.colors.LogNorm())

ax.set_xlabel('L1 Offset Time [ns]')
ax.set_ylabel('ADC Value')

plt.tight_layout()

ax.set_xlim(0, 250)
ax.annotate(f'H2GCROC3 Beam Test', xy=(0.02, 0.97), xycoords='axes fraction', fontsize=20, color='black', weight='bold', ha='left', va='top')
ax.annotate(f'Phase Scan, 200 GeV Hadrons', xy=(0.02, 0.91), xycoords='axes fraction', fontsize=18, color='black', ha='left', va='top')
ax.annotate(f'Channel {L1_scan_channel}', xy=(0.02, 0.86), xycoords='axes fraction', fontsize=18, color='black', ha='left', va='top')
ax.annotate(f'2024-05-28', xy=(0.02, 0.81), xycoords='axes fraction', fontsize=18, color='black', ha='left', va='top')


output_file_name = "PhaseScan_" + str(phase_array[0]) + "_" + str(phase_array[-1]) + ".png"
output_file_folder = "dump"
if not os.path.exists(output_file_folder):
    os.makedirs(output_file_folder)

output_file_name = os.path.join(output_file_folder, output_file_name)
plt.savefig(output_file_name)


fig_2, ax_2 = plt.subplots(1, 1, figsize=(12, 6), dpi = 300)
# make the histogram
ax_2.hist(hist_tot, bins=(machine_gun_bins)*16, range=(machine_gun_min, machine_gun_max), histtype='step', color='black')
ax_2.set_title('ToT')

# make vertical lines
for _phase in range(16):
    ax_2.axvline(x=_phase, color='red', linestyle='--')

plt.tight_layout()

ax_2.set_xlim(0, 11)
output_file_name = "ToT_" + str(phase_array[0]) + "_" + str(phase_array[-1]) + ".png"
output_file_name = os.path.join(output_file_folder, output_file_name)
plt.savefig(output_file_name)

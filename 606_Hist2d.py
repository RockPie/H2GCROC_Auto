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
script_id_str       = '606_Hist2d'
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
parser.add_argument('-o', '--output', type=str, help='Output file name')
parser.add_argument('-i', '--input', type=str, help='Input file name')
parser.add_argument('-n', '--num', type=int, help='Number of events to process')
parser.add_argument('-a', '--show_A', action='store_true', help='Show A side data')
parser.add_argument('-b', '--show_B', action='store_true', help='Show B side data')

args = parser.parse_args()

if args.input is None:
    logger.error('No input file specified')
    exit()

showing_A = args.show_A
showing_B = args.show_B
if showing_A and showing_B:
    logger.error('Cannot show both A and B side data in the same time')
    exit()

if not showing_A and not showing_B:
    logger.error('No board specified')
    exit()

# * --- Read the input file -------------------------------------------
input_file_name = args.input
input_file_folder = 'data'
input_file_path = os.path.join(input_file_folder, input_file_name)

if not os.path.exists(input_file_path):
    logger.error(f'Input file {input_file_path} does not exist')
    exit()

logger.info(f'Reading input file {input_file_path}')

# * --- Read the input file -------------------------------------------
_fragment_life = 100
_fragment_drop_counter = 0

with open(input_file_path, 'r') as f:
    extracted_payloads_pool = []
    event_fragment_pool     = []
    fragment_life_dict      = {}

    current_event_num = 0
    expected_event_num = 1000 if args.num is None else args.num

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
                        # logger.warning(f'Fragment {timestamp0} is not complete')
                        _fragment_drop_counter += 1
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

# * --- Plot the data ------------------------------------------------
fig, [ax0, ax1, ax2] = plt.subplots(3, 1, figsize=(12, 12), dpi = 300, sharex=False, sharey=False)

hist2d_x_v0_chns = []
hist2d_x_v1_chns = []
hist2d_x_v2_chns = []
hist2d_y_v0_values = []
hist2d_y_v1_values = []
hist2d_y_v2_values = []

for _event in range(expected_event_num):
    # if machine_gun_counter_pack[_event] != 3:
    #     continue
    for _chn in range(152):
        hist2d_x_v0_chns.append(_chn)
        hist2d_x_v1_chns.append(_chn)
        hist2d_x_v2_chns.append(_chn)
        hist2d_y_v0_values.append(all_chn_value_0_array[_event][_chn])
        tot_value = int(all_chn_value_1_array[_event][_chn])
        if (tot_value >> 9) & 0x1 == 1:
            tot_value = (tot_value & 0x1FF) << 3
        hist2d_y_v1_values.append(tot_value)
        hist2d_y_v2_values.append(all_chn_value_2_array[_event][_chn])

ax0.hist2d(hist2d_x_v0_chns, hist2d_y_v0_values, bins=(152, 256), range=((0, 152), (0, 1024)), cmap=plt.cm.jet, norm=mpl.colors.LogNorm())
if showing_A:
    ax0.set_title('Channel vs. ADC (Board 208)')
if showing_B:
    ax0.set_title('Channel vs. ADC (Board 209)')

# ax0.annotate(f'H2GCROC3 Beam Test', xy=(0.01, 0.93), xycoords='axes fraction', ha='left', va='center', fontsize=20, color='red', weight='bold')
# ax0.annotate(f'350 GeV Hadrons, SPS H2', xy=(0.01, 0.86), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')
# ax0.annotate(f'with FoCal-H Prototype 2', xy=(0.01, 0.79), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')
# ax0.annotate(f'2024-05-27', xy=(0.01, 0.72), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')

ax0.annotate(f'ADC Values', xy=(0.99, 0.93), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
ax0.annotate(f'{expected_event_num} Events', xy=(0.99, 0.86), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
if showing_A:
    ax0.annotate(f'Board 208', xy=(0.99, 0.79), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
if showing_B:
    ax0.annotate(f'Board 209', xy=(0.99, 0.79), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')


ax1.hist2d(hist2d_x_v1_chns, hist2d_y_v1_values, bins=(152, 256), range=((0, 152), (0, 4096)), cmap=plt.cm.jet, norm=mpl.colors.LogNorm())
if showing_A:
    ax1.set_title('Channel vs. ToT (Board 208)')
if showing_B:
    ax1.set_title('Channel vs. ToT (Board 209)')

base_x_offset = 0.18
ax1.annotate(f'H2GCROC3 Beam Test', xy=(0.01 + base_x_offset, 0.93), xycoords='axes fraction', ha='left', va='center', fontsize=20, color='red', weight='bold')
ax1.annotate(f'350 GeV Hadrons, SPS H2', xy=(0.01 + base_x_offset, 0.86), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')
ax1.annotate(f'with FoCal-H Prototype 2', xy=(0.01 + base_x_offset, 0.79), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')
ax1.annotate(f'2024-05-27', xy=(0.01 + base_x_offset, 0.72), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')

ax1.annotate(f'TOT Values', xy=(0.99, 0.93), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
ax1.annotate(f'{expected_event_num} Events', xy=(0.99, 0.86), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
if showing_A:
    ax1.annotate(f'Board 208', xy=(0.99, 0.79), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
if showing_B:
    ax1.annotate(f'Board 209', xy=(0.99, 0.79), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')


ax2.hist2d(hist2d_x_v2_chns, hist2d_y_v2_values, bins=(152, 256), range=((0, 152), (0, 1024)), cmap=plt.cm.jet, norm=mpl.colors.LogNorm())
if showing_A:
    ax2.set_title('Channel vs. ToA (Board 208)')
if showing_B:
    ax2.set_title('Channel vs. ToA (Board 209)')

# ax2.annotate(f'H2GCROC3 Beam Test', xy=(0.01, 0.93), xycoords='axes fraction', ha='left', va='center', fontsize=20, color='red', weight='bold')
# ax2.annotate(f'350 GeV Hadrons, SPS H2', xy=(0.01, 0.86), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')
# ax2.annotate(f'with FoCal-H Prototype 2', xy=(0.01, 0.79), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')
# ax2.annotate(f'2024-05-27', xy=(0.01, 0.72), xycoords='axes fraction', ha='left', va='center', fontsize=16, color='red')

ax2.annotate(f'TOA Values', xy=(0.99, 0.93), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
ax2.annotate(f'{expected_event_num} Events', xy=(0.99, 0.86), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
if showing_A:
    ax2.annotate(f'Board 208', xy=(0.99, 0.79), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')
if showing_B:
    ax2.annotate(f'Board 209', xy=(0.99, 0.79), xycoords='axes fraction', ha='right', va='center', fontsize=16, color='black', weight='bold')


#tight_layout automatically adjusts subplot params so that the subplot(s) fits in to the figure area.
plt.tight_layout()

if args.output is not None:
    output_file_path = os.path.join('dump', args.output)
    logger.info(f'Saving output file {output_file_path}')
    plt.savefig(output_file_path)
else:
    output_file_name = input_file_name.split('.')[0] + '_hist2d' + time.strftime("_%Y%m%d_%H%M%S", time.localtime()) + '.png'
    output_file_path = os.path.join('dump', output_file_name)
    logger.info(f'Saving output file {output_file_path}')
    plt.savefig(output_file_path)

L1_scan_channel = 6

hist_1d_x = []
hist_1d_y = []

for _event in range(expected_event_num):
    hist_1d_x.append(machine_gun_counter_pack[_event])
    hist_1d_y.append(all_chn_value_0_array[_event][L1_scan_channel])

fig, ax = plt.subplots(1, 1, figsize=(12, 6), dpi = 300)
machine_gun_min = min(machine_gun_counter_pack)
machine_gun_max = 10
machine_gun_bins = machine_gun_max - machine_gun_min + 1
ax.hist2d(hist_1d_x, hist_1d_y, bins=(machine_gun_bins+2, 256), range=((machine_gun_min - 1, machine_gun_max + 1), (0, 1024)), cmap=plt.cm.jet, norm=mpl.colors.LogNorm())
ax.set_title('Machine Gun Counter vs. ToT')

plt.tight_layout()

if args.output is not None:
    output_file_path = os.path.join('dump', args.output)
    logger.info(f'Saving output file {output_file_path}')
    plt.savefig(output_file_path)
else:
    output_file_name = input_file_name.split('.')[0] + '_hist1d' + time.strftime("_%Y%m%d_%H%M%S", time.localtime()) + '.png'
    output_file_path = os.path.join('dump', output_file_name)
    logger.info(f'Saving output file {output_file_path}')
    plt.savefig(output_file_path)


logger.info(f'Fragment drop counter: {_fragment_drop_counter}')

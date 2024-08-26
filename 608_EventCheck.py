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
script_id_str       = '608_EventCheck'
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

# * --- Set up input file ---------------------------------------

input_folder = 'data'
input_file = 'Run028.txt'

ASIC_0_half_0_counter = 0
ASIC_0_half_1_counter = 0
ASIC_1_half_0_counter = 0
ASIC_1_half_1_counter = 0
ASIC_2_half_0_counter = 0
ASIC_2_half_1_counter = 0
ASIC_3_half_0_counter = 0
ASIC_3_half_1_counter = 0

_fragment_life = 10

ASIC_half_line_counters = [0] * 40
abnormal_counter = 0

current_event_num = 0
expected_event_num = 40000

all_chn_value_0_array = np.zeros((expected_event_num, 152))
all_chn_value_1_array = np.zeros((expected_event_num, 152))
all_chn_value_2_array = np.zeros((expected_event_num, 152))
hamming_code_array    = np.zeros((expected_event_num, 12))

extracted_payloads_pool = []
event_fragment_pool     = []
fragment_life_dict      = {}

last_timestamp = 0
timestamp_diff_pack = []
machine_gun_counter_pack = []

machine_gun_counter = 0
timestamp_diff_threshold = 100

good_packet_header_counter = 0
bad_packet_header_counter = 0

with open(os.path.join(input_folder, input_file), 'r') as f:
    for line in f:
        line_normal_flag = True
        # if it starts with a #, it is a comment
        if line.startswith('#'):
            continue
        # if it is not a comment, it is a data line

        data = line.split()

        if data[0] == 'A0' and data[1] == '00' and data[2] == '24':
            ASIC_0_half_0_counter += 1
            _line_cnt_base = 0
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                # if start with 5, like 0x5D, it is a good packet header
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        elif data[0] == 'A0' and data[1] == '00' and data[2] == '25':
            ASIC_0_half_1_counter += 1
            _line_cnt_base = 5
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        elif data[0] == 'A1' and data[1] == '00' and data[2] == '24':
            ASIC_1_half_0_counter += 1
            _line_cnt_base = 10
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        elif data[0] == 'A1' and data[1] == '00' and data[2] == '25':
            ASIC_1_half_1_counter += 1
            _line_cnt_base = 15
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        elif data[0] == 'A0' and data[1] == '01' and data[2] == '24':
            ASIC_2_half_0_counter += 1
            _line_cnt_base = 20
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        elif data[0] == 'A0' and data[1] == '01' and data[2] == '25':
            ASIC_2_half_1_counter += 1
            _line_cnt_base = 25
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        elif data[0] == 'A1' and data[1] == '01' and data[2] == '24':
            ASIC_3_half_0_counter += 1
            _line_cnt_base = 30
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        elif data[0] == 'A1' and data[1] == '01' and data[2] == '25':
            ASIC_3_half_1_counter += 1
            _line_cnt_base = 35
            if data[3] == '00':
                ASIC_half_line_counters[0 + _line_cnt_base] += 1
                if data[8].startswith('5') and data[11].endswith('5'):
                    good_packet_header_counter += 1
                else:
                    bad_packet_header_counter += 1
            elif data[3] == '01':
                ASIC_half_line_counters[1 + _line_cnt_base] += 1
            elif data[3] == '02':
                ASIC_half_line_counters[2 + _line_cnt_base] += 1
            elif data[3] == '03':
                ASIC_half_line_counters[3 + _line_cnt_base] += 1
            elif data[3] == '04':
                ASIC_half_line_counters[4 + _line_cnt_base] += 1
        else:
            abnormal_counter += 1
            line_normal_flag = False

        if not line_normal_flag:
            bytearray_line = bytearray()
            # transfer the line to bytearray
            for d in data:
                bytearray_line.append(int(d, 16))
        else:
            continue

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
        # if current_event_num == expected_event_num:
        #     break;      

logger.info(f'Event Counter: {current_event_num}')

logger.info(f'ASIC 0 half 0 counter: {ASIC_0_half_0_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[0:5]}')
logger.info(f'ASIC 0 half 1 counter: {ASIC_0_half_1_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[5:10]}')
logger.info(f'ASIC 1 half 0 counter: {ASIC_1_half_0_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[10:15]}')
logger.info(f'ASIC 1 half 1 counter: {ASIC_1_half_1_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[15:20]}')
logger.info(f'ASIC 2 half 0 counter: {ASIC_2_half_0_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[20:25]}')
logger.info(f'ASIC 2 half 1 counter: {ASIC_2_half_1_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[25:30]}')
logger.info(f'ASIC 3 half 0 counter: {ASIC_3_half_0_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[30:35]}')
logger.info(f'ASIC 3 half 1 counter: {ASIC_3_half_1_counter}')
logger.info(f'Line counters: {ASIC_half_line_counters[35:40]}')
logger.info(f'Abnormal packets: {abnormal_counter}')

logger.info(f'Good packet header counter: {good_packet_header_counter}')
logger.info(f'Bad packet header counter: {bad_packet_header_counter}')
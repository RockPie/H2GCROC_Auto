import matplotlib.pyplot as plt

import packetlib
import socket
import numpy as np
import time
import json
import os

from tqdm import tqdm

# Load the data
data_mother_folder = 'data'
data_folder = '104_PhaseScan_data_20240520_150100'
# output folder prefix is from the data folder name
output_folder_prefix = data_folder.split('_')[0] + '_' + data_folder.split('_')[1] + '_'
data_file_prefix = '104_PhaseScan'
data_folder_path = os.path.join(data_mother_folder, data_folder)
data_files = [f for f in os.listdir(data_folder_path) if f.startswith(data_file_prefix)]

print(f'Found {len(data_files)} data files in {data_folder_path}')

# delay values are following the file name pattern: phasescan_gendly_<delay>_phase_<phase>_data_20240518_183634
data_files_delay_values = [int(f.split('_')[3]) for f in data_files]
data_file_phase_values = [int(f.split('_')[5]) for f in data_files]

print(f'Delay values: {data_files_delay_values}')
print(f'Phase values: {data_file_phase_values}')

max_delay = max(data_files_delay_values)*16 + max(data_file_phase_values)
min_delay = min(data_files_delay_values)*16 + min(data_file_phase_values)

print(f'Delay values: {data_files_delay_values}')
print(f'Phase values: {data_file_phase_values}')

expected_event_num = 10
machine_gun_offset = 1
# Load the txt data

all_chn_scan_data_matrix =[]
all_chn_sample_index_matrix = []

for _file_index in range(len(data_files)):
    _file = data_files[_file_index]
    with open(os.path.join(data_folder_path, _file), 'r') as f:
        # get txt file line by line
        lines = f.readlines()
        lines_count = len(lines)
        print(f'Loaded {_file} with {lines_count} lines')
        extracted_payloads_pool = []
        event_fragment_pool     = []

        current_half_packet_num = 0
        current_event_num = 0

        all_chn_value_0_array = np.zeros((expected_event_num, 152))
        all_chn_value_1_array = np.zeros((expected_event_num, 152))
        all_chn_value_2_array = np.zeros((expected_event_num, 152))
        machinegun_sample_index_array = np.zeros((expected_event_num, 1))
        hamming_code_array = np.zeros((expected_event_num, 12))
        # read every 5 lines
        _line = 0
        _last_timestamp = 0
        sample_index = 0
        while _line < lines_count:
            # print(f'Line {_line}')
            # get the delay value
            line_data = lines[_line]
            line_bytearrays = []
            # split by space
            line_data = line_data.split(' ')
            # print(f'Line {_line}: {line_data}')
            for _byte in line_data:
                line_bytearrays.append(bytearray.fromhex(_byte))
            
            _array = line_bytearrays[0]
            timestamp = _array[4] << 24 | _array[5] << 16 | _array[6] << 8 | _array[7]
            timestamp_offset = timestamp - _last_timestamp
            _last_timestamp = timestamp
            # print("timestamp offset:" + str(timestamp_offset))
            if (abs(timestamp_offset) > 100):
                # print('new event')
                sample_index = 0
            elif (timestamp_offset > 5):
                # print('new sample')
                sample_index += 1
            event_fragment_pool.append(line_bytearrays)
            _line += 1
            # print('fragment pool size:' + str(len(event_fragment_pool)))
            indices_to_delete = set()
            if len(event_fragment_pool) >= 4:
                event_fragment_pool = sorted(event_fragment_pool, key=lambda x: x[0][3:7])
            i=0
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
                    
                    machinegun_sample_index_array[current_event_num] = sample_index
                    # print("current sample num:" + str(sample_index))
                    current_event_num += 1
                    i += 4
                else:
                    i += 1
            for index in sorted(indices_to_delete, reverse=True):
                del event_fragment_pool[index]
            # print("current event num:" + str(sample_index))
                # print('left fragments:' + str(len(event_fragment_pool)))
            if current_event_num == expected_event_num:
                break;

        _one_scan_data = []
        for _chn in range(152):
            _chn_values = []
            for _event in range(current_event_num):
                _chn_values.append(all_chn_value_0_array[_event][_chn])
            _one_scan_data.append(_chn_values)
        # print("channels:" + str(len(_one_scan_data)))
        all_chn_scan_data_matrix.append(_one_scan_data)
        all_chn_sample_index_matrix.append(machinegun_sample_index_array)

output_pics_folder_name = output_folder_prefix + time.strftime("%Y%m%d_%H%M%S") 
output_pics_folder_name = os.path.join('dump', output_pics_folder_name)

print("Saving channel-wise figures ...")
if not os.path.exists(output_pics_folder_name):
    os.makedirs(output_pics_folder_name) 
for _chn in range(152):
    figure_path = "Chn" + str(_chn) + '.png'
    _chn_val_x_vals = []
    _chn_val_y_vals = []
    _scan = 0
    for _index in range(len(data_files)):
        _delay = data_files_delay_values[_index]
        _phase = data_file_phase_values[_index]
        _timeValue = _delay*16 + _phase
        for _event in range(len(all_chn_scan_data_matrix[_scan][_chn])):
            # _chn_val_x_vals.append(_delay + int(machine_gun_offset * all_chn_sample_index_matrix[_scan][_event]))
            _chn_val_x_vals.append(_timeValue)
            _chn_val_y_vals.append(all_chn_scan_data_matrix[_scan][_chn][_event])
        _scan += 1

    figure_path = os.path.join(output_pics_folder_name, figure_path)
    fig_chn, ax_chn = plt.subplots(dpi=300)
    ax_chn.hist2d(_chn_val_x_vals, _chn_val_y_vals, bins=(np.linspace(min_delay,max_delay,(max_delay-min_delay)), np.linspace(0,512,256)))
    ax_chn.set_xlabel('Delay [25 ns]')
    ax_chn.set_ylabel('ADC Value')
    plt.savefig(figure_path)
    plt.close()

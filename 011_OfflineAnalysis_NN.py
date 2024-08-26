import packetlib
import socket
import numpy as np
import time
import json
import os

from tqdm import tqdm
import matplotlib.pyplot as plt

# Load the data
data_mother_folder = 'data'
data_file = 'InjectionTest.txt'


# Load the txt data

all_chn_scan_data_matrix =[]
all_chn_sample_index_matrix = []

try:
    with open(data_file, 'r') as f:
        # get txt file line by line
        lines = f.readlines()
        lines_count = len(lines)
        extracted_payloads_pool = []
        event_fragment_pool     = []

        current_half_packet_num = 0
        current_event_num = 0

        expected_event_num = lines_count // 20
        all_chn_value_0_array = np.zeros((expected_event_num, 152))
        all_chn_value_1_array = np.zeros((expected_event_num, 152))
        all_chn_value_2_array = np.zeros((expected_event_num, 152))
        machinegun_sample_index_array = np.zeros((expected_event_num, 1))
        hamming_code_array = np.zeros((expected_event_num, 12))
        # read every 5 lines
        _line = 0
        _last_timestamp = 0
        sample_index = 0
        for _line in range(0, lines_count, 5):
            line_data0 = lines[_line]
            line_data1 = lines[_line+1]
            line_data2 = lines[_line+2]
            line_data3 = lines[_line+3]
            line_data4 = lines[_line+4]

            if not line_data0[0] == line_data1[0] == line_data2[0] == line_data3[0] == line_data4[0]:
                print("Error: data format error")
                break

            line_bytearrays = []

            line_bytearrays.append(bytearray.fromhex(line_data0.strip()))
            line_bytearrays.append(bytearray.fromhex(line_data1.strip()))
            line_bytearrays.append(bytearray.fromhex(line_data2.strip()))
            line_bytearrays.append(bytearray.fromhex(line_data3.strip()))
            line_bytearrays.append(bytearray.fromhex(line_data4.strip()))
            
            _array = line_bytearrays[0]
            timestamp = _array[4] << 24 | _array[5] << 16 | _array[6] << 8 | _array[7]
            timestamp_offset = timestamp - _last_timestamp
            _last_timestamp = timestamp
            print("timestamp offset:" + str(timestamp_offset))
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
                    print("current sample num:" + str(sample_index))
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

except Exception as e:
    print("Error reading the data file: " + str(e))
    exit()

output_pics_folder_name = 'test_output'
output_pics_folder_name = os.path.join('dump', output_pics_folder_name)


machine_gun_offset = 1
print("Saving channel-wise figures ...")
if not os.path.exists(output_pics_folder_name):
    os.makedirs(output_pics_folder_name) 
for _chn in range(152):
    figure_path = "Chn" + str(_chn) + '.png'
    _chn_val_x_vals = []
    _chn_val_y_vals = []
    _scan = 0

    for _event in range(len(all_chn_scan_data_matrix[_scan][_chn])):
        _chn_val_x_vals.append(int(machine_gun_offset * all_chn_sample_index_matrix[_scan][_event]))
        # _chn_val_x_vals.append(_delay)
        _chn_val_y_vals.append(all_chn_scan_data_matrix[_scan][_chn][_event])
    _scan += 1

    figure_path = os.path.join(output_pics_folder_name, figure_path)
    fig_chn, ax_chn = plt.subplots(dpi=300)
    ax_chn.hist2d(_chn_val_x_vals, _chn_val_y_vals, bins=(np.linspace(0,15,15), np.linspace(0,512,256)))
    ax_chn.set_xlabel('Delay [25 ns]')
    ax_chn.set_ylabel('ADC Value')
    plt.savefig(figure_path)
    plt.close()

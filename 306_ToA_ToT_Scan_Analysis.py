import packetlib
import socket
import numpy as np
import time
import json
import os
import logging
import colorlog
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib as mpl

# * --- Set up script information -------------------------------------
script_id_str       = '306_ToA_ToT_Scan_Analysis'
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

def get_toa_value(toa_global, toa_trim):
    return toa_global + toa_trim

# * --- Set up data folder ---------------------------------------------
data_mother_folder = 'data'
input_data_folder_name  = '106_ToA_ToT_Scan_data_20240521_181859'
gen_nr_cyc = 10
machine_gun = 0

input_data_folder  = os.path.join(data_mother_folder, input_data_folder_name)

input_data_files = [f for f in os.listdir(input_data_folder) if f.startswith('106_ToA_ToT_Scan')]
logger.info(f'Found {len(input_data_files)} data files in {input_data_folder}')

# names are like: 106_ToA_ToT_Scan_internal_512_data_20240521_162439
input_data_internal_12b_values = [int(f.split('_')[5]) for f in input_data_files]
input_data_internal_12b_values_unique = list(set(input_data_internal_12b_values))
logger.info(f'Internal 12b values: {input_data_internal_12b_values_unique}')

max_threshold = max(input_data_internal_12b_values_unique)
min_threshold = min(input_data_internal_12b_values_unique)
logger.info(f'Internal 12b dac values: {min_threshold} - {max_threshold}')

output_mother_folder = 'dump'
output_pics_folder_name = input_data_folder_name + '_output_' + time.strftime("%Y%m%d_%H%M%S")
output_pics_folder_name = os.path.join(output_mother_folder, output_pics_folder_name)

expected_event_num = gen_nr_cyc*(machine_gun+1)

all_chn_scan_data_val0_matrix = []
all_chn_scan_data_val1_matrix = []
all_chn_scan_data_val2_matrix = []
all_chn_sample_index_matrix = []

progress_bar = tqdm(range(len(input_data_files)))
for _file_index in progress_bar:
    progress_bar.set_description(f'Processing file {_file_index+1}/{len(input_data_files)}')
    with open(os.path.join(input_data_folder, input_data_files[_file_index]), 'r') as f:
        lines = f.readlines()
        lines_count = len(lines)
        # logger.info(f'Loaded {input_data_files[_file_index]} with {lines_count} lines')

        extracted_payloads_pool = []
        event_fragment_pool     = []

        current_half_packet_num = 0
        current_event_num = 0

        all_chn_value_0_array = np.zeros((expected_event_num, 152))
        all_chn_value_1_array = np.zeros((expected_event_num, 152))
        all_chn_value_2_array = np.zeros((expected_event_num, 152))
        hamming_code_array = np.zeros((expected_event_num, 12))

        machinegun_sample_index_array = np.zeros((expected_event_num, 1))

        _line = 0
        _last_timestamp = 0
        sample_index = 0

        while _line < lines_count - 4:
            _line_bytearrays = []
            for _line_offset in range(5):
                # each line the bytes are separated by space
                _line_bytearrays.append(bytearray.fromhex(lines[_line+_line_offset].strip()))
            
            _timestamp = _line_bytearrays[0][4] << 24 | _line_bytearrays[0][5] << 16 | _line_bytearrays[0][6] << 8 | _line_bytearrays[0][7]
            _timestamp_offset = _timestamp - _last_timestamp
            _last_timestamp = _timestamp

            if (abs(_timestamp_offset) > 100):
                sample_index = 0
            elif (_timestamp_offset > 5):
                sample_index += 1
            
            event_fragment_pool.append(_line_bytearrays)
            _line += 5
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
            # logger.debug(f'Current event num: {current_event_num}')
            if current_event_num == expected_event_num:
                break;

        _one_scan_data_val0 = []
        _one_scan_data_val1 = []
        _one_scan_data_val2 = []
        for _chn in range(152):
            _chn_values_val0 = []
            _chn_values_val1 = []
            _chn_values_val2 = []
            for _event in range(current_event_num):
                _chn_values_val0.append(all_chn_value_0_array[_event][_chn])
                tot_val = all_chn_value_1_array[_event][_chn]
                if int(tot_val) >> 9 == 1:
                    tot_val = tot_val * 8
                _chn_values_val1.append(tot_val)
                _chn_values_val2.append(all_chn_value_2_array[_event][_chn])
            _one_scan_data_val0.append(_chn_values_val0)
            _one_scan_data_val1.append(_chn_values_val1)
            _one_scan_data_val2.append(_chn_values_val2)

        
        # print("channels:" + str(len(_one_scan_data)))
        all_chn_scan_data_val0_matrix.append(_one_scan_data_val0)
        all_chn_scan_data_val1_matrix.append(_one_scan_data_val1)
        all_chn_scan_data_val2_matrix.append(_one_scan_data_val2)
        all_chn_sample_index_matrix.append(machinegun_sample_index_array)

if not os.path.exists(output_pics_folder_name):
    os.makedirs(output_pics_folder_name) 

progress_bar_saving = tqdm(range(152))
for _chn in progress_bar_saving:
    progress_bar_saving.set_description(f'Saving channel {_chn+1}/152')
    figure_path = "Chn" + str(_chn) + '.png'
    _chn_val_x_val0s = []
    _chn_val_y_val0s = []
    _chn_val_x_val1s = []
    _chn_val_y_val1s = []
    _chn_val_x_val2s = []
    _chn_val_y_val2s = []

    _scan = 0
    for _index in range(len(input_data_files)):
        _internal_12b_val = input_data_internal_12b_values[_index]
        for _event in range(len(all_chn_scan_data_val0_matrix[_scan][_chn])):
            # _chn_val_x_vals.append(_delay + int(machine_gun_offset * all_chn_sample_index_matrix[_scan][_event]))
            _chn_val_x_val0s.append(_internal_12b_val)
            _chn_val_y_val0s.append(all_chn_scan_data_val0_matrix[_scan][_chn][_event])
            _chn_val_x_val1s.append(_internal_12b_val)
            _chn_val_y_val1s.append(all_chn_scan_data_val1_matrix[_scan][_chn][_event])
            _chn_val_x_val2s.append(_internal_12b_val)
            _chn_val_y_val2s.append(all_chn_scan_data_val2_matrix[_scan][_chn][_event])
        _scan += 1

    figure_path = os.path.join(output_pics_folder_name, figure_path)
    fig_chn, ax_chn = plt.subplots(dpi=300)
    # ax_chn.hist2d(_chn_val_x_val0s, _chn_val_y_val0s, bins=(np.linspace(min_threshold,max_threshold,len(input_data_files)), np.linspace(0,1024,512)), norm=mpl.colors.LogNorm())
    ax_chn.hist2d(_chn_val_x_val1s, _chn_val_y_val1s, bins=(np.linspace(min_threshold,max_threshold,len(input_data_files)), np.linspace(0,4096, 512)), norm=mpl.colors.LogNorm())
    # ax_chn.hist2d(_chn_val_x_val2s, _chn_val_y_val2s, bins=(np.linspace(min_threshold,max_threshold,len(input_data_files)), np.linspace(0,1024,512)), norm=mpl.colors.LogNorm())
    ax_chn.set_xlabel('Internal 12b DAC Value')
    ax_chn.set_ylabel('Values')
    plt.savefig(figure_path)
    plt.close()
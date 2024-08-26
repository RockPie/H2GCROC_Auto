import packetlib
import socket
from tqdm import tqdm
from itertools import groupby
import matplotlib.pyplot as plt
import numpy as np
import time
import json
import os

# * UDP Settings
# * ---------------------------------------------------------------------------
output_file_path = "dump"
output_json_name = "daq_push_config_" + time.strftime("%Y%m%d_%H%M%S") + ".json"
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

# * I2C register settings
# * ---------------------------------------------------------------------------

i2c_settings_json_path = "h2gcroc_1v4_r1.json"
reg_settings = packetlib.RegisterSettings(i2c_settings_json_path)

# * Parameters
# * ---------------------------------------------------------------------------
total_asic      = 2
fpga_address    = 0x00

i2c_setting_verbose = False

output_json["options"] = {}
output_json["options"]["total_asic"]        = total_asic
output_json["options"]["fpga_address"]      = fpga_address

# * Get and print the status of the device
# * ---------------------------------------------------------------------------
data_packet = packetlib.pack_data_req_status(0xA0, 0x00)
socket_udp.sendto(data_packet, (h2gcroc_ip, h2gcroc_port))
received_data, addr = socket_udp.recvfrom(1024)
unpacked_data = packetlib.unpack_data_rpy_status(received_data)
if unpacked_data is not None:
    output_json["status"] = unpacked_data

for asic in range(2):
    if not packetlib.send_check_DAQ_gen_params(socket_udp, h2gcroc_ip, h2gcroc_port, asic, fpga_addr=fpga_address, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_pre_fcmd=75, gen_fcmd=75, gen_preimp_en=0, gen_pre_interval=0x000A, gen_nr_of_cycle=1, gen_interval=0x01800000, daq_push_fcmd=75, machine_gun=0x01,verbose=False):
        if True:
            print('\033[33m' + "Warning: Generator parameters not match" + '\033[0m')

# * Write the config to all ASICs
# * ---------------------------------------------------------------------------
# default_top_reg = reg_settings.get_default_reg_content('registers_top')
# reg_settings.explain_reg_content(default_top_reg, 'registers_top')
i2c_content_top = [0x0B,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
# reg_settings.explain_reg_content(i2c_content_top, 'registers_top')

output_json["i2c_config"] = {}
output_json["i2c_config"]["i2c_content_top"] = i2c_content_top

for test_loop_counter in range(1):
    for i in range(total_asic):
        print('\033[34m' + "Setting i2c content for ASIC " + str(i) + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=i2c_content_top, verbose=i2c_setting_verbose):
            print('\033[33m' + "Warning in sending i2c content for Top" + '\033[0m')

# * Send DAQ push and receive data
# * ---------------------------------------------------------------------------
print('\033[34m' + "Setting DAQ Push" + '\033[0m')

for loop_cnt in tqdm(range(1), desc="DAQ Push", unit="loop"):

    if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=0, fpga_addr = fpga_address, daq_push=0xFF, gen_start_stop=0, daq_start_stop=0xFF, verbose=False):
        print('\033[33m' + "Warning in sending DAQ Push" + '\033[0m')

    # print('\033[34m' + "Receiving DAQ Push" + '\033[0m')
    header_byte_array   = bytearray()
    all_chn_value_0_arrary = np.zeros((152, 1))
    all_chn_value_1_arrary = np.zeros((152, 1))
    all_chn_value_2_arrary = np.zeros((152, 1))

    while True:
        try:
            data_packet, addr   = socket_udp.recvfrom(8192)
            header_byte_array   = data_packet[0:12]
            data_byte_array     = data_packet[12:812]
            extracted_payloads  = packetlib.extract_raw_payloads(data_packet)
            print(extracted_payloads)
            sorted_and_grouped  = packetlib.sort_and_group_40bytes(extracted_payloads)
            if sorted_and_grouped is None:
                continue
            for i in range(len(sorted_and_grouped)): # four groups for all half-asics
                # check if the values are nonetype
                if sorted_and_grouped[i] is None:
                    continue
                for j in range(len(sorted_and_grouped[i])):
                    # print in hex with one space
                    print(sorted_and_grouped[i][j].hex(), end='\n')
                print()
            for i in range(len(sorted_and_grouped)): # four groups for all half-asics
                extracted_data = packetlib.assemble_data_from_40bytes(sorted_and_grouped[i], verbose=False)
                extracted_values = packetlib.extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
                uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
                for j in range(len(extracted_values["_extracted_values"])):
                    all_chn_value_0_arrary[j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
                    all_chn_value_1_arrary[j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
                    all_chn_value_2_arrary[j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
            break
        except Exception as e:
            print('\033[33m' + "Error in receiving DAQ Push" + '\033[0m')
            print(e)

    fig0_0, ax0_0 = plt.subplots()
    ax0_0.plot(all_chn_value_0_arrary, 'r')
    ax0_0.set_title('Val 0')
    ax0_0.set_xlabel('Channel')
    ax0_0.set_ylabel('Value')
    # mark x-axis 0, 19, 38, 57, 76, 95, 114, 133
    ax0_0.vlines(x=[0, 19, 38, 57, 76, 95, 114, 133, 152], ymin=0, ymax=1023, colors='k', linestyles='dashed', alpha=0.5)
    ax0_0.hlines(y=[0, 511, 1023], xmin=0, xmax=152, colors='k', linestyles='dashed', alpha=0.5)
    ax0_0.set_xlim([0, 152])
    ax0_0.set_ylim([0, 1023])
    fig0_0.tight_layout()
    fig0_0.savefig(os.path.join(output_file_path, "daq_push_chn0_" + time.strftime("%Y%m%d_%H%M%S") + ".png"))

    fig0_1, ax0_1 = plt.subplots()
    ax0_1.plot(all_chn_value_1_arrary, 'g')
    ax0_1.set_title('Val 1')
    ax0_1.set_xlabel('Channel')
    ax0_1.set_ylabel('Value')
    ax0_1.vlines(x=[0, 19, 38, 57, 76, 95, 114, 133, 152], ymin=0, ymax=1023, colors='k', linestyles='dashed', alpha=0.5)
    ax0_1.hlines(y=[0, 511, 1023], xmin=0, xmax=152, colors='k', linestyles='dashed', alpha=0.5)
    ax0_1.set_xlim([0, 152])
    ax0_1.set_ylim([0, 1023])
    fig0_1.tight_layout()
    fig0_1.savefig(os.path.join(output_file_path, "daq_push_chn1_" + time.strftime("%Y%m%d_%H%M%S") + ".png"))

    fig0_2, ax0_2 = plt.subplots()
    ax0_2.plot(all_chn_value_2_arrary, 'b')
    ax0_2.set_title('Val 2')
    ax0_2.set_xlabel('Channel')
    ax0_2.set_ylabel('Value')
    ax0_2.vlines(x=[0, 19, 38, 57, 76, 95, 114, 133, 152], ymin=0, ymax=1023, colors='k', linestyles='dashed', alpha=0.5)
    ax0_2.hlines(y=[0, 511, 1023], xmin=0, xmax=152, colors='k', linestyles='dashed', alpha=0.5)
    ax0_2.set_xlim([0, 152])
    ax0_2.set_ylim([0, 1023])
    fig0_2.tight_layout()
    fig0_2.savefig(os.path.join(output_file_path, "daq_push_chn2_" + time.strftime("%Y%m%d_%H%M%S") + ".png"))


# * Write the config to all ASICs
# * ---------------------------------------------------------------------------
i2c_content_top = [0x08,0x0f,0x40,0x7f,0x00,0x07,0x85,0x00]
# reg_settings.explain_reg_content(i2c_content_top, 'registers_top')

output_json["i2c_config"]["i2c_content_top_re"] = i2c_content_top

for test_loop_counter in range(1):
    for i in range(total_asic):
        print('\033[34m' + "Setting i2c content for ASIC " + str(i) + '\033[0m')
        if not packetlib.send_check_i2c(socket_udp, h2gcroc_ip, h2gcroc_port, asic_num=i, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=i2c_content_top, verbose=i2c_setting_verbose):
            print('\033[33m' + "Warning in sending i2c content for Top" + '\033[0m')

# * Write to file
# * ---------------------------------------------------------------------------
with open(output_json_path, 'w') as json_file:
    json.dump(output_json, json_file, indent=4)

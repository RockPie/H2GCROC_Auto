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

# * --- Set up script information -------------------------------------
script_id_str       = '605_DAQ'
script_version_str  = '0.2'

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
default_output_file_name = script_id_str + time.strftime("_%Y%m%d_%H%M%S", time.localtime()) + '.txt'
parser = argparse.ArgumentParser(description='DAQ script for data acquisition')
parser.add_argument('-o', '--output', type=str, help='Output file name', default=default_output_file_name)
parser.add_argument('-c', '--config', type=str, help='Configuration file name')
parser.add_argument('-n', '--num', type=int, help='Number of events to acquire', default=100)
parser.add_argument('-a', '--A', action='store_true', help='Acquire data from board A')
parser.add_argument('-b', '--B', action='store_true', help='Acquire data from board B')

args = parser.parse_args()

event_num = args.num
if event_num <= 0:
    logger.critical(f"Invalid number of events: {event_num}")
    exit()

if not args.A and not args.B:
    logger.critical("So from which board should I acquire data?")
    exit()

# * --- Set up output folder -------------------------------------------
output_folder = 'data'
config_folder = 'dump'

if not os.path.exists(output_folder):
    os.makedirs(output_folder)
if not os.path.exists(config_folder):
    logger.critical(f"Configuration folder {config_folder} does not exist!")
    exit()

# * --- Set up UDP communication --------------------------------------
h2gcroc_ip_A    = "10.1.2.208"
h2gcroc_port_A  = 11000
h2gcroc_ip_B    = "10.1.2.209"
h2gcroc_port_B  = 11000

pc_ip           = "10.1.2.207"
pc_port         = 11000
timeout         = 3 # seconds

logger.info(f"Board A H2G IP: {h2gcroc_ip_A}")
logger.info(f"Board A H2G Port: {h2gcroc_port_A}")
logger.info(f"Board B H2G IP: {h2gcroc_ip_B}")
logger.info(f"Board B H2G Port: {h2gcroc_port_B}")

ping_result = ping(pc_ip, count=1)
if ping_result.is_alive:
    logger.info(f"PC IP {pc_ip} is reachable")
else:
    logger.critical(f"PC IP {pc_ip} is not reachable")
    logger.critical("Please check the network settings")
    exit()

socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_udp.bind((pc_ip, pc_port))
# socket_udp.settimeout(timeout)

# * --- Find the configuration file ------------------------------------
config_file = args.config

if config_file is None:
    config_file_prefix = '604_SystemConfig_runtime'
    config_candidates = [f for f in os.listdir(config_folder) if f.startswith(config_file_prefix) and f.endswith('.json')]
    if len(config_candidates) == 0:
        logger.critical(f"No configuration file found in {config_folder}")
        exit()
    config_candidates.sort(reverse=True)

    config_file = os.path.join(config_folder, config_candidates[0])
    logger.info(f"Configuration file {config_file} is selected")
else:
    config_file = os.path.join(config_folder, config_file)
    if not os.path.exists(config_file):
        logger.critical(f"Configuration file {config_file} does not exist!")
        exit()

config_json = json.load(open(config_file, 'r'))
top_reg_runLR = config_json['i2c']['top_reg_runLR']
top_reg_offLR = config_json['i2c']['top_reg_offLR']

info_generator = config_json['generator']
info_input = config_json['input']

output_file_name = os.path.join(output_folder, args.output)

# if the file already exists, ask for confirmation
if os.path.exists(output_file_name):
    logger.warning(f"Output file {output_file_name} already exists")
    user_input = input("Do you want to overwrite it? (y/n): ")
    if user_input.lower() != 'y':
        logger.info("User cancelled the operation")
        exit()

with open(output_file_name, 'w') as f:
    # write info block
    f.write(f"#########################################################\n")
    f.write(f"# KCU-H2GCROC DAQ\n")
    f.write(f"# Script ID: {script_id_str}\n")
    f.write(f"# Script Version: {script_version_str} by Shihai. J\n")
    f.write(f"# Configuration file: {config_file}\n")
    f.write(f"# Output file: {args.output}\n")
    f.write(f"# Number of events: {event_num}\n")
    f.write(f"# Board A: {args.A}\n")
    f.write(f"# Board B: {args.B}\n")
    f.write(f"# Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
    f.write(f"#########################################################\n")
    # * --- Set up data acquisition ----------------------------------------
    try:
        # set up top register
        if args.A:
            fpga_address = 0x00
            for _asic in range(2):
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
                    logger.warning(f"Failed to set Top settings RunLR for ASIC {_asic} for run on board A")
        if args.B:
            fpga_address = 0x01
            for _asic in range(2):
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_runLR, retry=5, verbose=False):
                    logger.warning(f"Failed to set Top settings RunLR for ASIC {_asic} for run on board B")

        packetlib.clean_socket(socket_udp)

        # set up generator
        
        if args.A:
            fpga_address = 0x00
            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0xFF, verbose=False):
                logger.warning(f"Failed to start generator for board A")

        if args.B:
            fpga_address = 0x01
            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0xFF, verbose=False):
                logger.warning(f"Failed to start generator for board B")

        current_packet_num = 0
        expected_packet_num = event_num * 4 * (2 if args.A and args.B else 1) * (config_json["generator"]["machine_gun_val"] + 1) * config_json["generator"]["gen_nr_cycle"]
        logger.info(f"Expected number of packets: {expected_packet_num}")

        extracted_payloads_pool = []

        progress_bar = tqdm(total=expected_packet_num, desc="Acquiring data", unit="packets")
        progress_divider = expected_packet_num // 100

        # ! acquire data
        while True:
            try:
                # set the progress bar by the current packet number
                rec_data, rec_addr = socket_udp.recvfrom(65536)
                extracted_payloads_pool += packetlib.extract_raw_payloads(rec_data)
                while len(extracted_payloads_pool) >= 5:
                    candidate_packet_lines = extracted_payloads_pool[:5]
                    is_packet_good, event_fragment = packetlib.check_event_fragment(candidate_packet_lines)
                    if is_packet_good:
                        extracted_payloads_pool = extracted_payloads_pool[5:]
                        current_packet_num += 1
                        for _byte_line in event_fragment:
                            hex_data = ' '.join([f'{_byte:02X}' for _byte in _byte_line])
                            f.write(hex_data + '\n')
                        if current_packet_num%progress_divider == 0:
                            progress_bar.update(progress_divider)
                    else:
                        extracted_payloads_pool = extracted_payloads_pool[1:]
                if current_packet_num >= expected_packet_num:
                    progress_bar.close()
                    break
            except socket.timeout:
                logger.warning("UDP Timeout")
                break

        # ! end of data acquisition

        if args.A:
            fpga_address = 0x00
            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
                logger.warning(f"Failed to start generator for board A")

        if args.B:
            fpga_address = 0x01
            if not packetlib.send_daq_gen_start_stop(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=0, fpga_addr = fpga_address, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=False):
                logger.warning(f"Failed to start generator for board B")

        # set up off register
        if args.A:
            fpga_address = 0x00
            for _asic in range(2):
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_A, h2gcroc_port_A, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
                    logger.warning(f"Failed to set Top settings OffLR for ASIC {_asic} for run on board A")
        if args.B:
            fpga_address = 0x01
            for _asic in range(2):
                if not packetlib.send_check_i2c_wrapper(socket_udp, h2gcroc_ip_B, h2gcroc_port_B, asic_num=_asic, fpga_addr = fpga_address, sub_addr=packetlib.subblock_address_dict["Top"], reg_addr=0x00, data=top_reg_offLR, retry=5, verbose=False):
                    logger.warning(f"Failed to set Top settings OffLR for ASIC {_asic} for run on board B")

    finally:
        socket_udp.close()
        logger.info("UDP socket is closed")

logger.info(f"Data acquisition is finished. Data is saved to {output_file_name}")



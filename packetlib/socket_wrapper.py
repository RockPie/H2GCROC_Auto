import socket
from .packet import *
import time

def clean_socket(_socket):
    """ Attempt to clean out any remaining data in the socket buffer. """
    _timeout_value = _socket.gettimeout()
    _socket.settimeout(0.01)  # Set a short timeout to quickly skip through any remaining data
    try:
        for i in range(100):
            data = _socket.recv(8192)  # Attempt to read socket buffer
            if not data:
                break
    except socket.timeout:
        pass
    finally:
        _socket.settimeout(_timeout_value)

def send_check_i2c(_socket, addr, port, asic_num, fpga_addr, sub_addr, reg_addr, data, verbose=True):
    data_len = len(data)
    if data_len > 32:
        if verbose:
            print(f"Data length is too long: {data_len}")
        return
    if data_len == 0:
        if verbose:
            print("Data length is zero")
        return
    if verbose:
        print("\033[32mSending data packet:\033[0m")
    header = 0xA0 + asic_num
    subaddr_10_3 = (sub_addr >> 3) & 0xFF
    subaddr_2_0 = sub_addr & 0x07
    data_packet = pack_data_req_i2c_write(header, fpga_addr, 0x00, data_len, subaddr_10_3, subaddr_2_0, reg_addr, data + [0x00] * (32 - data_len))
    if verbose:
        for i in range(0, len(data_packet), 8):
            print(" ".join(f"{b:02X}" for b in data_packet[i:i+8]))
    _socket.sendto(data_packet, (addr, port))

    read_req_packet = pack_data_req_i2c_read(header, fpga_addr, 0x01, data_len, subaddr_10_3, subaddr_2_0, reg_addr)
    clean_socket(_socket)
    _socket.sendto(read_req_packet, (addr, port))
    if verbose:
        print("\033[32mReceived data packet:\033[0m")
    try:
        received_data, addr = _socket.recvfrom(8196)
        if verbose:
            for i in range(0, len(received_data), 8):
                print(" ".join(f"{b:02X}" for b in received_data[i:i+8]))
        unpacked_data = unpack_data_rpy_i2c_read(received_data)
        max_key_length = max(len(key) for key in unpacked_data)
        if verbose:
            for key in unpacked_data:
                if key == "data":
                    print(f"{key:<{max_key_length}} : {' '.join(f'{b:02X}' for b in unpacked_data[key])}")
                else: 
                    print(f"{key:<{max_key_length}} : {hex(unpacked_data[key])}")

        input_data_array = bytearray(data)
        received_data_array = bytearray(unpacked_data["data"])[0:len(input_data_array)]
        if input_data_array == received_data_array:
            if verbose:
                print("\033[32mData matches\033[0m")
            return True
        else:
            if verbose:
                print("\033[31mData does not match\033[0m")
            return False
    except socket.timeout:
        if verbose:
            print("\033[31mTimeout\033[0m")
        return False
    
def send_check_i2c_wrapper(_socket, addr, port, asic_num, fpga_addr, sub_addr, reg_addr, data, retry=3, verbose=True):
    for i in range(retry):
        if send_check_i2c(_socket, addr, port, asic_num, fpga_addr, sub_addr, reg_addr, data, verbose):
            return True
    if verbose:
        print("\033[31mFailed to send data to sub: {sub_addr}, reg: {reg_addr}\033[0m")
    time.sleep(0.1)
    return False

    
def read_save_all_i2c(file_name, _socket, addr, port, asic_num, fpga_addr):
    # get all i2c subaddresses from subblock_address_dict
    # get all keys
    keys = subblock_address_dict.keys()
    output_content = {}
    for key in keys:
        # get all subaddresses
        sub_addr = subblock_address_dict[key]
        header = 0xA0 + asic_num
        subaddr_10_3 = (sub_addr >> 3) & 0xFF
        subaddr_2_0 = sub_addr & 0x07
        read_req_packet = pack_data_req_i2c_read(header, fpga_addr, 0x01, 32, subaddr_10_3, subaddr_2_0, 0x00)
        # print all data types
        _socket.sendto(read_req_packet, (addr, port))
        received_data, rec_addr = _socket.recvfrom(8196)
        unpacked_data = unpack_data_rpy_i2c_read(received_data)
        output_content[key] = unpacked_data["data"]
    with open(file_name, "w") as f:
        # write the dictionary to the file
        # as txt file and one line for each key, in hex
        for key in output_content:
            f.write(key + " : " + " ".join(f"{b:02X}" for b in output_content[key]) + "\n")
    
def send_check_DAQ_gen_params(socket, addr, port, asic_num, fpga_addr, data_coll_en=0x00, trig_coll_en=0x00, daq_fcmd=0x00, gen_pre_fcmd=0x00, gen_fcmd=0x00, ext_trg_en=0x00, ext_trg_delay=0x00, ext_trg_deadtime=0x00, gen_preimp_en=0x00, gen_pre_interval=0x0000, gen_nr_of_cycle=0x00000000, gen_interval=0x00000000, daq_push_fcmd=0x00, machine_gun=0x00, ext_trg_out_0_len=0x00, ext_trg_out_1_len=0x00, ext_trg_out_2_len=0x00, ext_trg_out_3_len=0x00, verbose=True, readback=True):
    if ext_trg_en > 0x01 or gen_preimp_en > 0x01:
        if verbose:
            print("Parameter value is too large")
        return False
    header = 0xA0 + asic_num
    data_packet = pack_data_req_daq_gen_write(header, fpga_addr, data_coll_en, trig_coll_en, daq_fcmd, gen_pre_fcmd, gen_fcmd, ext_trg_en, ext_trg_delay, ext_trg_deadtime, gen_preimp_en, gen_pre_interval, gen_nr_of_cycle, gen_interval, daq_push_fcmd, machine_gun, ext_trg_out_0_len, ext_trg_out_1_len, ext_trg_out_2_len, ext_trg_out_3_len)
    if verbose:
        print("\033[32mSending data packet:\033[0m")
        for i in range(0, len(data_packet), 8):
            print(" ".join(f"{b:02X}" for b in data_packet[i:i+8]))
    socket.sendto(data_packet, (addr, port))
    data_packet_req_read = pack_data_req_daq_gen_read(header, fpga_addr)
    clean_socket(socket)
    if readback:
        socket.sendto(data_packet_req_read, (addr, port))
        if verbose:
            print("\033[32mReceived data packet:\033[0m")
        received_data, addr = socket.recvfrom(8196)
        if verbose:
            for i in range(0, len(received_data), 8):
                print(" ".join(f"{b:02X}" for b in received_data[i:i+8]))
        unpacked_data = unpack_data_rpy_rpy_daq_gen_read(received_data)
        max_key_length = max(len(key) for key in unpacked_data)
        if verbose:
            for key in unpacked_data:
                print(f"{key:<{max_key_length}} : {hex(unpacked_data[key])}")
        if bytearray(received_data[7:]) == data_packet[7:]:
            return True
        else:
            return False
    return True

def set_bitslip(socket, addr, port, asic_num, fpga_addr, io_dly_sel, a0_io_dly_val_fclk, a0_io_dly_val_fcmd, a0_io_dly_val_tr0, a0_io_dly_val_tr1, a0_io_dly_val_tr2, a0_io_dly_val_tr3, a0_io_dly_val_dq0, a0_io_dly_val_dq1, a1_io_dly_val_fclk, a1_io_dly_val_fcmd, a1_io_dly_val_tr0, a1_io_dly_val_tr1, a1_io_dly_val_tr2, a1_io_dly_val_tr3, a1_io_dly_val_dq0, a1_io_dly_val_dq1, verbose=True):
    if a0_io_dly_val_fclk > 0x4FF or a0_io_dly_val_fcmd > 0x4FF or a0_io_dly_val_tr0 > 0x1FF or a0_io_dly_val_tr1 > 0x1FF or a0_io_dly_val_tr2 > 0x1FF or a0_io_dly_val_tr3 > 0x1FF or a0_io_dly_val_dq0 > 0x1FF or a0_io_dly_val_dq1 > 0x1FF or a1_io_dly_val_fclk > 0x4FF or a1_io_dly_val_fcmd > 0x4FF or a1_io_dly_val_tr0 > 0x1FF or a1_io_dly_val_tr1 > 0x1FF or a1_io_dly_val_tr2 > 0x1FF or a1_io_dly_val_tr3 > 0x1FF or a1_io_dly_val_dq0 > 0x1FF or a1_io_dly_val_dq1 > 0x1FF:
        if verbose:
            print("Delay value is too large")
        return False
    header = 0xA0 + asic_num
    a0_io_dlyo_fclk_10_9  = (a0_io_dly_val_fclk >> 9) & 0x03
    a0_io_dlyo_fclk_8_1   = (a0_io_dly_val_fclk >> 1) & 0xFF
    a0_io_dlyo_fcmd_10_9  = (a0_io_dly_val_fcmd >> 9) & 0x03
    a0_io_dlyo_fcmd_8_1   = (a0_io_dly_val_fcmd >> 1) & 0xFF
    a0_io_dly_val_tr0_8_1 = (a0_io_dly_val_tr0 >> 1)  & 0xFF
    a0_io_dly_val_tr1_8_1 = (a0_io_dly_val_tr1 >> 1)  & 0xFF
    a0_io_dly_val_tr2_8_1 = (a0_io_dly_val_tr2 >> 1)  & 0xFF
    a0_io_dly_val_tr3_8_1 = (a0_io_dly_val_tr3 >> 1)  & 0xFF
    a0_io_dly_val_dq0_8_1 = (a0_io_dly_val_dq0 >> 1)  & 0xFF
    a0_io_dly_val_dq1_8_1 = (a0_io_dly_val_dq1 >> 1)  & 0xFF
    a1_io_dlyo_fclk_10_9  = (a1_io_dly_val_fclk >> 9) & 0x03
    a1_io_dlyo_fclk_8_1   = (a1_io_dly_val_fclk >> 1) & 0xFF
    a1_io_dlyo_fcmd_10_9  = (a1_io_dly_val_fcmd >> 9) & 0x03
    a1_io_dlyo_fcmd_8_1   = (a1_io_dly_val_fcmd >> 1) & 0xFF
    a1_io_dly_val_tr0_8_1 = (a1_io_dly_val_tr0 >> 1)  & 0xFF
    a1_io_dly_val_tr1_8_1 = (a1_io_dly_val_tr1 >> 1)  & 0xFF
    a1_io_dly_val_tr2_8_1 = (a1_io_dly_val_tr2 >> 1)  & 0xFF
    a1_io_dly_val_tr3_8_1 = (a1_io_dly_val_tr3 >> 1)  & 0xFF
    a1_io_dly_val_dq0_8_1 = (a1_io_dly_val_dq0 >> 1)  & 0xFF
    a1_io_dly_val_dq1_8_1 = (a1_io_dly_val_dq1 >> 1)  & 0xFF

    a0_io_delay_bit0 = (a0_io_dly_val_fclk & 0x01) << 7 | (a0_io_dly_val_fcmd & 0x01) << 6 | (a0_io_dly_val_tr0 & 0x01) << 5 | (a0_io_dly_val_tr1 & 0x01) << 4 | (a0_io_dly_val_tr2 & 0x01) << 3 | (a0_io_dly_val_tr3 & 0x01) << 2 | (a0_io_dly_val_dq0 & 0x01) << 1 | (a0_io_dly_val_dq1 & 0x01)
    a1_io_delay_bit0 = (a1_io_dly_val_fclk & 0x01) << 7 | (a1_io_dly_val_fcmd & 0x01) << 6 | (a1_io_dly_val_tr0 & 0x01) << 5 | (a1_io_dly_val_tr1 & 0x01) << 4 | (a1_io_dly_val_tr2 & 0x01) << 3 | (a1_io_dly_val_tr3 & 0x01) << 2 | (a1_io_dly_val_dq0 & 0x01) << 1 | (a1_io_dly_val_dq1 & 0x01)

    data_packet = pack_data_req_set_bitslip(header, fpga_addr, io_dly_sel, a0_io_dlyo_fclk_10_9, a0_io_dlyo_fcmd_10_9, a0_io_dlyo_fclk_8_1, a0_io_dlyo_fcmd_8_1, a0_io_dly_val_tr0_8_1, a0_io_dly_val_tr1_8_1, a0_io_dly_val_tr2_8_1, a0_io_dly_val_tr3_8_1, a0_io_dly_val_dq0_8_1, a0_io_dly_val_dq1_8_1, a0_io_delay_bit0, a1_io_dlyo_fclk_10_9, a1_io_dlyo_fcmd_10_9, a1_io_dlyo_fclk_8_1, a1_io_dlyo_fcmd_8_1, a1_io_dly_val_tr0_8_1, a1_io_dly_val_tr1_8_1, a1_io_dly_val_tr2_8_1, a1_io_dly_val_tr3_8_1, a1_io_dly_val_dq0_8_1, a1_io_dly_val_dq1_8_1, a1_io_delay_bit0)
    if verbose:
        print("\033[32mSending data packet:\033[0m")
        for i in range(0, len(data_packet), 8):
            print(" ".join(f"{b:02X}" for b in data_packet[i:i+8]))
    socket.sendto(data_packet, (addr, port))

    req_get_bitslip_packet = pack_data_req_get_bitslip(header, fpga_addr)
    socket.sendto(req_get_bitslip_packet, (addr, port))
    if verbose:
        print("\033[32mReceived data packet:\033[0m")
    received_data, addr = socket.recvfrom(8196)
    if verbose:
        for i in range(0, len(received_data), 8):
            print(" ".join(f"{b:02X}" for b in received_data[i:i+8]))
    unpacked_data = unpack_data_rpy_get_bitslip(received_data)
    if unpacked_data == None:
        if verbose:
            print("\033[31mData does not match\033[0m")
        return False
    max_key_length = max(len(key) for key in unpacked_data)
    if verbose:
        for key in unpacked_data:
            print(f"{key:<{max_key_length}} : {hex(unpacked_data[key])}")
    match_flag = True
    match_flag = match_flag and (int(unpacked_data["a0_io_dlyo_fclk"]) == a0_io_dly_val_fclk) and (int(unpacked_data["a0_io_dlyo_fcmd"]) == a0_io_dly_val_fcmd) and (int(unpacked_data["a0_io_delay_tr0"]) == a0_io_dly_val_tr0) and (int(unpacked_data["a0_io_delay_tr1"]) == a0_io_dly_val_tr1) and (int(unpacked_data["a0_io_delay_tr2"]) == a0_io_dly_val_tr2) and (int(unpacked_data["a0_io_delay_tr3"]) == a0_io_dly_val_tr3) and (int(unpacked_data["a0_io_delay_dq0"]) == a0_io_dly_val_dq0) and (int(unpacked_data["a0_io_delay_dq1"]) == a0_io_dly_val_dq1) and (int(unpacked_data["a1_io_dlyo_fclk"]) == a1_io_dly_val_fclk) and (int(unpacked_data["a1_io_dlyo_fcmd"]) == a1_io_dly_val_fcmd) and (int(unpacked_data["a1_io_delay_tr0"]) == a1_io_dly_val_tr0) and (int(unpacked_data["a1_io_delay_tr1"]) == a1_io_dly_val_tr1) and (int(unpacked_data["a1_io_delay_tr2"]) == a1_io_dly_val_tr2) and (int(unpacked_data["a1_io_delay_tr3"]) == a1_io_dly_val_tr3) and (int(unpacked_data["a1_io_delay_dq0"]) == a1_io_dly_val_dq0) and (int(unpacked_data["a1_io_delay_dq1"]) == a1_io_dly_val_dq1)
    if match_flag and verbose:
        print("\033[32mData matches\033[0m")
    elif not match_flag and verbose:
        print("\033[31mData does not match\033[0m")
    return match_flag

def send_reset_adj(socket, addr, port, asic_num, fpga_addr, sw_hard_reset_sel, sw_hard_reset, sw_soft_reset_sel, sw_soft_reset, sw_i2c_reset_sel, sw_i2c_reset, reset_pack_counter, adjustable_start, verbose=True):
    if sw_hard_reset_sel > 0xFF or sw_hard_reset > 0x01 or sw_soft_reset_sel > 0xFF or sw_soft_reset > 0x01 or sw_i2c_reset_sel > 0xFF or sw_i2c_reset > 0x01 or reset_pack_counter > 0xFF or adjustable_start > 0xFF:
        if verbose:
            print("Reset value is too large")
        return False
    header = 0xA0 + asic_num
    data_packet = pack_data_req_reset_adj(header, fpga_addr, sw_hard_reset_sel, sw_hard_reset, sw_soft_reset_sel, sw_soft_reset, sw_i2c_reset_sel, sw_i2c_reset, reset_pack_counter, adjustable_start)
    if verbose:
        print("\033[32mSending data packet:\033[0m")
        for i in range(0, len(data_packet), 8):
            print(" ".join(f"{b:02X}" for b in data_packet[i:i+8]))
    socket.sendto(data_packet, (addr, port))
    return True

def get_system_monitor(socket, addr, port, asic_num, fpga_addr, verbose=True):
    header = 0xA0 + asic_num
    data_packet = pack_data_req_sys_monitor(header, fpga_addr)
    if verbose:
        print("\033[32mSending data packet:\033[0m")
        for i in range(0, len(data_packet), 8):
            print(" ".join(f"{b:02X}" for b in data_packet[i:i+8]))
    socket.sendto(data_packet, (addr, port))
    if verbose:
        print("\033[32mReceived data packet:\033[0m")
    received_data, addr = socket.recvfrom(8196)
    unpacked_data = unpack_data_rpy_sys_monitor(received_data)
    max_key_length = max(len(key) for key in unpacked_data)
    if verbose:
        for key in unpacked_data:
            print(f"{key:<{max_key_length}} : {hex(unpacked_data[key])}")
    return unpacked_data

def get_debug_data(socket, addr, port, asic_num, fpga_addr, verbose=True):
    header = 0xA0 + asic_num
    data_packet = pack_data_req_get_debug_data(header, fpga_addr)
    if verbose:
        print("\033[32mSending data packet:\033[0m")
        for i in range(0, len(data_packet), 8):
            print(" ".join(f"{b:02X}" for b in data_packet[i:i+8]))
    socket.sendto(data_packet, (addr, port))
    if verbose:
        print("\033[32mReceived data packet:\033[0m")
    received_data, addr = socket.recvfrom(8196)
    if verbose:
        for i in range(0, len(received_data), 8):
            print(" ".join(f"{b:02X}" for b in received_data[i:i+8]))
    unpacked_data = unpack_data_rpy_get_debug_data(received_data)
    if unpacked_data == None:
        if verbose:
            print("\033[31mData does not match\033[0m")
        return None
    max_key_length = max(len(key) for key in unpacked_data)
    if verbose:
        for key in unpacked_data:
            print(f"{key:<{max_key_length}} : {hex(unpacked_data[key])}")
    return unpacked_data

def send_daq_gen_start_stop(socket, addr, port, asic_num, fpga_addr, daq_push, gen_start_stop, daq_start_stop, verbose=True):
    if gen_start_stop > 0x01:
        return False
    header = 0xA0 + asic_num
    data_packet = pack_data_req_daq_gen_start(header, fpga_addr, daq_push, gen_start_stop, daq_start_stop)
    if verbose:
        print("\033[32mSending data packet:\033[0m")
        for i in range(0, len(data_packet), 8):
            print(" ".join(f"{b:02X}" for b in data_packet[i:i+8]))
    socket.sendto(data_packet, (addr, port))
    return True
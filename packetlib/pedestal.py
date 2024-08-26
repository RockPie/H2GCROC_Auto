from .socket_wrapper import *
from .packet import *
from .data_packet import *
import time
import numpy as np

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

def set_and_measure_pedestal(udp_socket, addr, port, fpga_addr, trim_inv_list, inv_vref_list, noinv_vref_list, channel_to_ignore, default_chn_content, default_reference_content, top_run_content, top_stop_content, generator_n_cyc, generator_interval, _verbose=1):
    # verify the length of the trim_inv_matrix, inv_vref_list, and noinv_vref_list
    if len(trim_inv_list) != 2*76:
        if _verbose > 0:
            print('\033[31m' + "Error: trim_inv_list length is not 2*76" + '\033[0m')
        return None
    if len(inv_vref_list) != 4:
        if _verbose > 0:
            print('\033[31m' + "Error: inv_vref_list length is not 4" + '\033[0m')
        return None
    if len(noinv_vref_list) != 4:
        if _verbose  > 0:
            print('\033[31m' + "Error: noinv_vref_list length is not 4" + '\033[0m')
        return None
    
    # set the top registers
    # print("Setting the top registers")
    for asic in range(2):
        if not send_check_i2c(udp_socket, addr, port, asic_num=asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Top"], reg_addr=0x00, data=top_run_content, verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(asic) + '\033[0m')
    
    # set the pedestal values
    # print("Setting the pedestal values")
    for _chn in range(2*76):
        _sub_addr = uni_chn_to_subblock_list[_chn % 76]
        _half_num = _chn // 38
        _asic_num = _chn // 76
        
        # copy the default content
        _chn_content = default_chn_content.copy()
        _chn_content[3] = (trim_inv_list[_chn] << 2) & 0xFC

        if not send_check_i2c(udp_socket, addr, port, asic_num=_asic_num, fpga_addr = fpga_addr, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
            if not send_check_i2c(udp_socket, addr, port, asic_num=_asic_num, fpga_addr = fpga_addr, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
                if _verbose > 0:
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')
            else:
                if _verbose > 0:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')

    # set reference voltages
    # print("Setting the reference voltages")
    for _asic in range(2):
        _ref_content_half0 = default_reference_content.copy()
        _ref_content_half1 = default_reference_content.copy()
        _ref_content_half0[4] = inv_vref_list[_asic*2] >> 2
        _ref_content_half1[4] = inv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[5] = noinv_vref_list[_asic*2] >> 2
        _ref_content_half1[5] = noinv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_list[_asic*2] & 0x03) << 2) | (noinv_vref_list[_asic*2] & 0x03)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_list[_asic*2+1] & 0x03) << 2) | (noinv_vref_list[_asic*2+1] & 0x03)

        if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=_verbose > 1):
            if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=_verbose > 1):
                if _verbose > 0:
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                if _verbose > 0:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
        
        if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=_verbose > 1):
            if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=_verbose > 1):
                if _verbose > 0:
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                if _verbose > 0:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

    # set the generator
    for asic in range(2):
        if not send_check_DAQ_gen_params(udp_socket, addr, port, asic, fpga_addr=fpga_addr, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_pre_fcmd=75, gen_fcmd=75, gen_preimp_en=0, gen_pre_interval=0x000A, gen_nr_of_cycle=generator_n_cyc, gen_interval=generator_interval, daq_push_fcmd=75, machine_gun=0x00,verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: Generator parameters not match" + '\033[0m')

    
    expected_half_packet_num = generator_n_cyc * 4
    expected_event_num = generator_n_cyc
    daqh_array = np.zeros((generator_n_cyc*4, 4))
    all_chn_value_0_array = np.zeros((expected_event_num, 152))
    all_chn_value_1_array = np.zeros((expected_event_num, 152))
    all_chn_value_2_array = np.zeros((expected_event_num, 152))
    hamming_code_array = np.zeros((expected_event_num, 12))

    # enable the generator
    if not send_daq_gen_start_stop(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, daq_push=0x00, gen_start_stop=1, daq_start_stop=0x03, verbose=_verbose > 1):
        if _verbose > 0:
            print('\033[33m' + "Warning in generator start" + '\033[0m')

    extracted_payloads = []
    event_fragment_pool = []
    current_half_packet_num = 0
    current_event_num = 0

    while True:
        try:
            data_packet, rec_addr   = udp_socket.recvfrom(8192)
            extracted_payloads += extract_raw_payloads(data_packet)
            if len(extracted_payloads) >= 5:
                while len(extracted_payloads) >= 5:
                    candidate_packet_lines = extracted_payloads[:5]
                    is_packet_good, event_fragment = check_event_fragment(candidate_packet_lines)
                    if is_packet_good:
                        event_fragment_pool.append(event_fragment)
                        current_half_packet_num += 1
                        extracted_payloads = extracted_payloads[5:]
                    else:
                        print('\033[33m' + "Warning: Event fragment is not good" + '\033[0m')
                        extracted_payloads = extracted_payloads[1:]
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
                    for _half in range(4):
                        extracted_data = assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
                        extracted_values = extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
                        uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
                        for j in range(len(extracted_values["_extracted_values"])):
                            all_chn_value_0_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
                            all_chn_value_1_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
                            all_chn_value_2_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
                        hamming_code_array[current_event_num][_half*3+0] =  DaqH_get_H1(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+1] =  DaqH_get_H2(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+2] =  DaqH_get_H3(extracted_values["_DaqH"])
                    indices_to_delete.update([i, i+1, i+2, i+3])
                    current_event_num += 1
                    i += 4
                else:
                    i += 1
            for index in sorted(indices_to_delete, reverse=True):
                del event_fragment_pool[index]
            if current_half_packet_num >= expected_half_packet_num:
                break
        except Exception as e:
            if True:
                print('\033[33m' + "Warning: Exception in receiving data" + '\033[0m')
                print(e)
            break

    # set the top registers
    for asic in range(2):
        if not send_check_i2c(udp_socket, addr, port, asic_num=asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Top"], reg_addr=0x00, data=top_stop_content, verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: I2C readback does not match the sent stop data, asic: " + str(asic) + '\033[0m')
    
    # disable the generator
    if not send_daq_gen_start_stop(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=_verbose > 1):
        if _verbose > 0:
            print('\033[33m' + "Warning in generator start" + '\033[0m')
    
    all_chn_average_0 = np.zeros((152, 1))
    all_chn_average_1 = np.zeros((152, 1))
    all_chn_average_2 = np.zeros((152, 1))
    all_chn_error_0 = np.zeros((152, 1))
    all_chn_error_1 = np.zeros((152, 1))
    all_chn_error_2 = np.zeros((152, 1))

    half_0_average = 0
    half_1_average = 0
    half_2_average = 0
    half_3_average = 0

    half_0_std = 0
    half_1_std = 0
    half_2_std = 0
    half_3_std = 0

    for i in range(152):
        for j in range(generator_n_cyc):
            all_chn_average_0[i] += all_chn_value_0_array[j][i]
            all_chn_average_1[i] += all_chn_value_1_array[j][i]
            all_chn_average_2[i] += all_chn_value_2_array[j][i]
        all_chn_average_0[i] /= generator_n_cyc
        all_chn_average_1[i] /= generator_n_cyc
        all_chn_average_2[i] /= generator_n_cyc

        for j in range(generator_n_cyc):
            all_chn_error_0[i] += (all_chn_value_0_array[j][i] - all_chn_average_0[i]) ** 2
            all_chn_error_1[i] += (all_chn_value_1_array[j][i] - all_chn_average_1[i]) ** 2
            all_chn_error_2[i] += (all_chn_value_2_array[j][i] - all_chn_average_2[i]) ** 2
        if generator_n_cyc > 1:
            all_chn_error_0[i] = np.sqrt(all_chn_error_0[i]/(generator_n_cyc-1))
            all_chn_error_1[i] = np.sqrt(all_chn_error_1[i]/(generator_n_cyc-1))
            all_chn_error_2[i] = np.sqrt(all_chn_error_2[i]/(generator_n_cyc-1))
        else:
            all_chn_error_0[i] = 0
            all_chn_error_1[i] = 0
            all_chn_error_2[i] = 0

    # * Calculate half average
    half_0_average, half_0_std = calculate_segment_stats(all_chn_average_0, 0, 38, channel_to_ignore)
    half_1_average, half_1_std = calculate_segment_stats(all_chn_average_0, 38, 76, channel_to_ignore)
    half_2_average, half_2_std = calculate_segment_stats(all_chn_average_0, 76, 114, channel_to_ignore)
    half_3_average, half_3_std = calculate_segment_stats(all_chn_average_0, 114, 152, channel_to_ignore)

    return {
        "all_chn_average_0": all_chn_average_0,
        "all_chn_average_1": all_chn_average_1,
        "all_chn_average_2": all_chn_average_2,
        "daqh_array": daqh_array,  # "daqh_array" is a 4xN array where N is the number of cycles
        "all_chn_error_0": all_chn_error_0,
        "all_chn_error_1": all_chn_error_1,
        "all_chn_error_2": all_chn_error_2,
        "half_0_average": half_0_average,
        "half_1_average": half_1_average,
        "half_2_average": half_2_average,
        "half_3_average": half_3_average,
        "half_0_std": half_0_std,
        "half_1_std": half_1_std,
        "half_2_std": half_2_std,
        "half_3_std": half_3_std
    }

def fast_set_and_measure_pedestal(udp_socket, addr, port, fpga_addr, trim_inv_list, inv_vref_list, noinv_vref_list, channel_to_ignore, default_chn_content, default_reference_content, top_run_content, top_stop_content, generator_n_cyc, generator_interval, _verbose=1):
    # verify the length of the trim_inv_matrix, inv_vref_list, and noinv_vref_list
    if len(trim_inv_list) != 2*76:
        if _verbose > 0:
            print('\033[31m' + "Error: trim_inv_list length is not 2*76" + '\033[0m')
        return None
    if len(inv_vref_list) != 4:
        if _verbose > 0:
            print('\033[31m' + "Error: inv_vref_list length is not 4" + '\033[0m')
        return None
    if len(noinv_vref_list) != 4:
        if _verbose  > 0:
            print('\033[31m' + "Error: noinv_vref_list length is not 4" + '\033[0m')
        return None
    
    # set the top registers
    # print("Setting the top registers")
    for asic in range(2):
        if not send_check_i2c(udp_socket, addr, port, asic_num=asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Top"], reg_addr=0x00, data=top_run_content, verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(asic) + '\033[0m')
    
    # set the pedestal values
    # print("Setting the pedestal values")
    # for _chn in range(2*76):
    #     _sub_addr = uni_chn_to_subblock_list[_chn % 76]
    #     _half_num = _chn // 38
    #     _asic_num = _chn // 76
        
    #     # copy the default content
    #     _chn_content = default_chn_content.copy()
    #     _chn_content[3] = (trim_inv_list[_chn] << 2) & 0xFC

    #     if not send_check_i2c(udp_socket, addr, port, asic_num=_asic_num, fpga_addr = fpga_addr, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
    #         if not send_check_i2c(udp_socket, addr, port, asic_num=_asic_num, fpga_addr = fpga_addr, sub_addr=_sub_addr, reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
    #             if _verbose > 0:
    #                 print('\033[33m' + "Warning: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')
    #         else:
    #             if _verbose > 0:
    #                 print('\033[32m' + "Fixed: I2C readback does not match the sent data, chn: " + str(_chn) + '\033[0m')
    _chn_content = default_chn_content.copy()
    _chn_content[3] = (trim_inv_list[3] << 2) & 0xFC

    if not send_check_i2c(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
        if not send_check_i2c(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
            pass
    if not send_check_i2c(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
        if not send_check_i2c(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
            pass
    if not send_check_i2c(udp_socket, addr, port, asic_num=1, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
        if not send_check_i2c(udp_socket, addr, port, asic_num=1, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_0"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
            pass
    if not send_check_i2c(udp_socket, addr, port, asic_num=1, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
        if not send_check_i2c(udp_socket, addr, port, asic_num=1, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["HalfWise_1"], reg_addr=0x00, data=_chn_content, verbose=_verbose > 1):
            pass


    
    # set reference voltages
    # print("Setting the reference voltages")
    for _asic in range(2):
        _ref_content_half0 = default_reference_content.copy()
        _ref_content_half1 = default_reference_content.copy()
        _ref_content_half0[4] = inv_vref_list[_asic*2] >> 2
        _ref_content_half1[4] = inv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[5] = noinv_vref_list[_asic*2] >> 2
        _ref_content_half1[5] = noinv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_list[_asic*2] & 0x03) << 2) | (noinv_vref_list[_asic*2] & 0x03)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_list[_asic*2+1] & 0x03) << 2) | (noinv_vref_list[_asic*2+1] & 0x03)

        if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=_verbose > 1):
            if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=_verbose > 1):
                if _verbose > 0:
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                if _verbose > 0:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
        
        if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=_verbose > 1):
            if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=_verbose > 1):
                if _verbose > 0:
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                if _verbose > 0:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

    # set the generator
    for asic in range(2):
        if not send_check_DAQ_gen_params(udp_socket, addr, port, asic, fpga_addr=fpga_addr, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_pre_fcmd=75, gen_fcmd=75, gen_preimp_en=0, gen_pre_interval=0x000A, gen_nr_of_cycle=generator_n_cyc, gen_interval=generator_interval, daq_push_fcmd=75, machine_gun=0x00,verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: Generator parameters not match" + '\033[0m')

    
    expected_half_packet_num = generator_n_cyc * 4
    expected_event_num = generator_n_cyc
    daqh_array = np.zeros((generator_n_cyc*4, 4))
    all_chn_value_0_array = np.zeros((expected_event_num, 152))
    all_chn_value_1_array = np.zeros((expected_event_num, 152))
    all_chn_value_2_array = np.zeros((expected_event_num, 152))
    hamming_code_array = np.zeros((expected_event_num, 12))

    # enable the generator
    if not send_daq_gen_start_stop(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, daq_push=0x00, gen_start_stop=1, daq_start_stop=0x03, verbose=_verbose > 1):
        if _verbose > 0:
            print('\033[33m' + "Warning in generator start" + '\033[0m')

    extracted_payloads = []
    event_fragment_pool = []
    current_half_packet_num = 0
    current_event_num = 0

    while True:
        try:
            data_packet, rec_addr   = udp_socket.recvfrom(8192)
            extracted_payloads += extract_raw_payloads(data_packet)
            if len(extracted_payloads) >= 5:
                while len(extracted_payloads) >= 5:
                    candidate_packet_lines = extracted_payloads[:5]
                    is_packet_good, event_fragment = check_event_fragment(candidate_packet_lines)
                    if is_packet_good:
                        event_fragment_pool.append(event_fragment)
                        current_half_packet_num += 1
                        extracted_payloads = extracted_payloads[5:]
                    else:
                        print('\033[33m' + "Warning: Event fragment is not good" + '\033[0m')
                        extracted_payloads = extracted_payloads[1:]
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
                    for _half in range(4):
                        extracted_data = assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
                        extracted_values = extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
                        uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
                        for j in range(len(extracted_values["_extracted_values"])):
                            all_chn_value_0_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
                            all_chn_value_1_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
                            all_chn_value_2_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
                        hamming_code_array[current_event_num][_half*3+0] =  DaqH_get_H1(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+1] =  DaqH_get_H2(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+2] =  DaqH_get_H3(extracted_values["_DaqH"])
                    indices_to_delete.update([i, i+1, i+2, i+3])
                    current_event_num += 1
                    i += 4
                else:
                    i += 1
            for index in sorted(indices_to_delete, reverse=True):
                del event_fragment_pool[index]
            if current_half_packet_num >= expected_half_packet_num:
                break
        except Exception as e:
            if True:
                print('\033[33m' + "Warning: Exception in receiving data" + '\033[0m')
                print(e)
            break

    # set the top registers
    for asic in range(2):
        if not send_check_i2c(udp_socket, addr, port, asic_num=asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Top"], reg_addr=0x00, data=top_stop_content, verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: I2C readback does not match the sent stop data, asic: " + str(asic) + '\033[0m')
    
    # disable the generator
    if not send_daq_gen_start_stop(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=_verbose > 1):
        if _verbose > 0:
            print('\033[33m' + "Warning in generator start" + '\033[0m')
    
    all_chn_average_0 = np.zeros((152, 1))
    all_chn_average_1 = np.zeros((152, 1))
    all_chn_average_2 = np.zeros((152, 1))
    all_chn_error_0 = np.zeros((152, 1))
    all_chn_error_1 = np.zeros((152, 1))
    all_chn_error_2 = np.zeros((152, 1))

    half_0_average = 0
    half_1_average = 0
    half_2_average = 0
    half_3_average = 0

    half_0_std = 0
    half_1_std = 0
    half_2_std = 0
    half_3_std = 0

    for i in range(152):
        for j in range(generator_n_cyc):
            all_chn_average_0[i] += all_chn_value_0_array[j][i]
            all_chn_average_1[i] += all_chn_value_1_array[j][i]
            all_chn_average_2[i] += all_chn_value_2_array[j][i]
        all_chn_average_0[i] /= generator_n_cyc
        all_chn_average_1[i] /= generator_n_cyc
        all_chn_average_2[i] /= generator_n_cyc

        for j in range(generator_n_cyc):
            all_chn_error_0[i] += (all_chn_value_0_array[j][i] - all_chn_average_0[i]) ** 2
            all_chn_error_1[i] += (all_chn_value_1_array[j][i] - all_chn_average_1[i]) ** 2
            all_chn_error_2[i] += (all_chn_value_2_array[j][i] - all_chn_average_2[i]) ** 2
        if generator_n_cyc > 1:
            all_chn_error_0[i] = np.sqrt(all_chn_error_0[i]/(generator_n_cyc-1))
            all_chn_error_1[i] = np.sqrt(all_chn_error_1[i]/(generator_n_cyc-1))
            all_chn_error_2[i] = np.sqrt(all_chn_error_2[i]/(generator_n_cyc-1))
        else:
            all_chn_error_0[i] = 0
            all_chn_error_1[i] = 0
            all_chn_error_2[i] = 0

    # * Calculate half average
    half_0_average, half_0_std = calculate_segment_stats(all_chn_average_0, 0, 38, channel_to_ignore)
    half_1_average, half_1_std = calculate_segment_stats(all_chn_average_0, 38, 76, channel_to_ignore)
    half_2_average, half_2_std = calculate_segment_stats(all_chn_average_0, 76, 114, channel_to_ignore)
    half_3_average, half_3_std = calculate_segment_stats(all_chn_average_0, 114, 152, channel_to_ignore)

    return {
        "all_chn_average_0": all_chn_average_0,
        "all_chn_average_1": all_chn_average_1,
        "all_chn_average_2": all_chn_average_2,
        "daqh_array": daqh_array,  # "daqh_array" is a 4xN array where N is the number of cycles
        "all_chn_error_0": all_chn_error_0,
        "all_chn_error_1": all_chn_error_1,
        "all_chn_error_2": all_chn_error_2,
        "half_0_average": half_0_average,
        "half_1_average": half_1_average,
        "half_2_average": half_2_average,
        "half_3_average": half_3_average,
        "half_0_std": half_0_std,
        "half_1_std": half_1_std,
        "half_2_std": half_2_std,
        "half_3_std": half_3_std
    }

def ref_set_and_measure_pedestal(udp_socket, addr, port, fpga_addr, trim_inv_list, inv_vref_list, noinv_vref_list, channel_to_ignore, default_chn_content, default_reference_content, top_run_content, top_stop_content, generator_n_cyc, generator_interval, _verbose=1):
    # verify the length of the trim_inv_matrix, inv_vref_list, and noinv_vref_list
    if len(trim_inv_list) != 2*76:
        if _verbose > 0:
            print('\033[31m' + "Error: trim_inv_list length is not 2*76" + '\033[0m')
        return None
    if len(inv_vref_list) != 4:
        if _verbose > 0:
            print('\033[31m' + "Error: inv_vref_list length is not 4" + '\033[0m')
        return None
    if len(noinv_vref_list) != 4:
        if _verbose  > 0:
            print('\033[31m' + "Error: noinv_vref_list length is not 4" + '\033[0m')
        return None
    
    # set the top registers
    # print("Setting the top registers")
    for asic in range(2):
        if not send_check_i2c(udp_socket, addr, port, asic_num=asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Top"], reg_addr=0x00, data=top_run_content, verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: I2C readback does not match the sent start data, asic: " + str(asic) + '\033[0m')

    # set reference voltages
    # print("Setting the reference voltages")
    for _asic in range(2):
        _ref_content_half0 = default_reference_content.copy()
        _ref_content_half1 = default_reference_content.copy()
        _ref_content_half0[4] = inv_vref_list[_asic*2] >> 2
        _ref_content_half1[4] = inv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[5] = noinv_vref_list[_asic*2] >> 2
        _ref_content_half1[5] = noinv_vref_list[_asic*2+1] >> 2
        _ref_content_half0[1] = (_ref_content_half0[1] & 0xF0) | ((inv_vref_list[_asic*2] & 0x03) << 2) | (noinv_vref_list[_asic*2] & 0x03)
        _ref_content_half1[1] = (_ref_content_half1[1] & 0xF0) | ((inv_vref_list[_asic*2+1] & 0x03) << 2) | (noinv_vref_list[_asic*2+1] & 0x03)

        if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=_verbose > 1):
            if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_0"], reg_addr=0x00, data=_ref_content_half0, verbose=_verbose > 1):
                if _verbose > 0:
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                if _verbose > 0:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
        
        if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=_verbose > 1):
            if not send_check_i2c(udp_socket, addr, port, asic_num=_asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Reference_Voltage_1"], reg_addr=0x00, data=_ref_content_half1, verbose=_verbose > 1):
                if _verbose > 0:
                    print('\033[33m' + "Warning: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')
            else:
                if _verbose > 0:
                    print('\033[32m' + "Fixed: I2C readback does not match the sent data, asic: " + str(_asic) + '\033[0m')

    # set the generator
    for asic in range(2):
        if not send_check_DAQ_gen_params(udp_socket, addr, port, asic, fpga_addr=fpga_addr, data_coll_en=0x03, trig_coll_en=0x00, daq_fcmd=75, gen_pre_fcmd=75, gen_fcmd=75, gen_preimp_en=0, gen_pre_interval=0x000A, gen_nr_of_cycle=generator_n_cyc, gen_interval=generator_interval, daq_push_fcmd=75, machine_gun=0x00,verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: Generator parameters not match" + '\033[0m')

    
    expected_half_packet_num = generator_n_cyc * 4
    expected_event_num = generator_n_cyc
    daqh_array = np.zeros((generator_n_cyc*4, 4))
    all_chn_value_0_array = np.zeros((expected_event_num, 152))
    all_chn_value_1_array = np.zeros((expected_event_num, 152))
    all_chn_value_2_array = np.zeros((expected_event_num, 152))
    hamming_code_array = np.zeros((expected_event_num, 12))

    # enable the generator
    if not send_daq_gen_start_stop(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, daq_push=0x00, gen_start_stop=1, daq_start_stop=0x03, verbose=_verbose > 1):
        if _verbose > 0:
            print('\033[33m' + "Warning in generator start" + '\033[0m')

    extracted_payloads = []
    event_fragment_pool = []
    current_half_packet_num = 0
    current_event_num = 0

    while True:
        try:
            data_packet, rec_addr   = udp_socket.recvfrom(8192)
            extracted_payloads += extract_raw_payloads(data_packet)
            if len(extracted_payloads) >= 5:
                while len(extracted_payloads) >= 5:
                    candidate_packet_lines = extracted_payloads[:5]
                    is_packet_good, event_fragment = check_event_fragment(candidate_packet_lines)
                    if is_packet_good:
                        event_fragment_pool.append(event_fragment)
                        current_half_packet_num += 1
                        extracted_payloads = extracted_payloads[5:]
                    else:
                        print('\033[33m' + "Warning: Event fragment is not good" + '\033[0m')
                        extracted_payloads = extracted_payloads[1:]
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
                    for _half in range(4):
                        extracted_data = assemble_data_from_40bytes(event_fragment_pool[i+_half], verbose=False)
                        extracted_values = extract_values(extracted_data["_extraced_160_bytes"], verbose=False)
                        uni_chn_base = (extracted_data["_header"] - 0xA0) * 76 + (extracted_data["_packet_type"] - 0x24) * 38
                        for j in range(len(extracted_values["_extracted_values"])):
                            all_chn_value_0_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][1]
                            all_chn_value_1_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][2]
                            all_chn_value_2_array[current_event_num][j+uni_chn_base] = extracted_values["_extracted_values"][j][3]
                        hamming_code_array[current_event_num][_half*3+0] =  DaqH_get_H1(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+1] =  DaqH_get_H2(extracted_values["_DaqH"])
                        hamming_code_array[current_event_num][_half*3+2] =  DaqH_get_H3(extracted_values["_DaqH"])
                    indices_to_delete.update([i, i+1, i+2, i+3])
                    current_event_num += 1
                    i += 4
                else:
                    i += 1
            for index in sorted(indices_to_delete, reverse=True):
                del event_fragment_pool[index]
            if current_half_packet_num >= expected_half_packet_num:
                break
        except Exception as e:
            if True:
                print('\033[33m' + "Warning: Exception in receiving data" + '\033[0m')
                print(e)
            break

    # set the top registers
    for asic in range(2):
        if not send_check_i2c(udp_socket, addr, port, asic_num=asic, fpga_addr = fpga_addr, sub_addr=subblock_address_dict["Top"], reg_addr=0x00, data=top_stop_content, verbose=_verbose > 1):
            if _verbose > 0:
                print('\033[33m' + "Warning: I2C readback does not match the sent stop data, asic: " + str(asic) + '\033[0m')
    
    # disable the generator
    if not send_daq_gen_start_stop(udp_socket, addr, port, asic_num=0, fpga_addr = fpga_addr, daq_push=0x00, gen_start_stop=0, daq_start_stop=0x00, verbose=_verbose > 1):
        if _verbose > 0:
            print('\033[33m' + "Warning in generator start" + '\033[0m')
    
    all_chn_average_0 = np.zeros((152, 1))
    all_chn_average_1 = np.zeros((152, 1))
    all_chn_average_2 = np.zeros((152, 1))
    all_chn_error_0 = np.zeros((152, 1))
    all_chn_error_1 = np.zeros((152, 1))
    all_chn_error_2 = np.zeros((152, 1))

    half_0_average = 0
    half_1_average = 0
    half_2_average = 0
    half_3_average = 0

    half_0_std = 0
    half_1_std = 0
    half_2_std = 0
    half_3_std = 0

    for i in range(152):
        for j in range(generator_n_cyc):
            all_chn_average_0[i] += all_chn_value_0_array[j][i]
            all_chn_average_1[i] += all_chn_value_1_array[j][i]
            all_chn_average_2[i] += all_chn_value_2_array[j][i]
        all_chn_average_0[i] /= generator_n_cyc
        all_chn_average_1[i] /= generator_n_cyc
        all_chn_average_2[i] /= generator_n_cyc

        for j in range(generator_n_cyc):
            all_chn_error_0[i] += (all_chn_value_0_array[j][i] - all_chn_average_0[i]) ** 2
            all_chn_error_1[i] += (all_chn_value_1_array[j][i] - all_chn_average_1[i]) ** 2
            all_chn_error_2[i] += (all_chn_value_2_array[j][i] - all_chn_average_2[i]) ** 2
        if generator_n_cyc > 1:
            all_chn_error_0[i] = np.sqrt(all_chn_error_0[i]/(generator_n_cyc-1))
            all_chn_error_1[i] = np.sqrt(all_chn_error_1[i]/(generator_n_cyc-1))
            all_chn_error_2[i] = np.sqrt(all_chn_error_2[i]/(generator_n_cyc-1))
        else:
            all_chn_error_0[i] = 0
            all_chn_error_1[i] = 0
            all_chn_error_2[i] = 0

    # * Calculate half average
    half_0_average, half_0_std = calculate_segment_stats(all_chn_average_0, 0, 38, channel_to_ignore)
    half_1_average, half_1_std = calculate_segment_stats(all_chn_average_0, 38, 76, channel_to_ignore)
    half_2_average, half_2_std = calculate_segment_stats(all_chn_average_0, 76, 114, channel_to_ignore)
    half_3_average, half_3_std = calculate_segment_stats(all_chn_average_0, 114, 152, channel_to_ignore)

    return {
        "all_chn_average_0": all_chn_average_0,
        "all_chn_average_1": all_chn_average_1,
        "all_chn_average_2": all_chn_average_2,
        "daqh_array": daqh_array,  # "daqh_array" is a 4xN array where N is the number of cycles
        "all_chn_error_0": all_chn_error_0,
        "all_chn_error_1": all_chn_error_1,
        "all_chn_error_2": all_chn_error_2,
        "half_0_average": half_0_average,
        "half_1_average": half_1_average,
        "half_2_average": half_2_average,
        "half_3_average": half_3_average,
        "half_0_std": half_0_std,
        "half_1_std": half_1_std,
        "half_2_std": half_2_std,
        "half_3_std": half_3_std
    }
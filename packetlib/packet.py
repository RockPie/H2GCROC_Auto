import struct

req_status_format           = '2BB37x'
req_reset_adj_format        = '2BB5x8B24x'
req_set_parameters_format   = '2BBB3xB32x'
req_sys_monitor_format      = '2BB37x'
req_i2c_read_format         = '2BB2x3B32x'
req_i2c_write_format        = '2BB2x3B32B'
req_get_bitslip_format      = '2BB37x'
req_set_bitslip_format      = '2BB5x11B6x10B5x'
req_get_debug_data_format   = '2BB37x'
req_get_pack_counter_format = '2BB37x'
req_daq_gen_start_format    = '2BBx3B33x'
req_daq_gen_read_format     = '2BB37x'
req_daq_gen_write_format    = '2BB2B2x19B2x4B8x'
req_daq_gen2_write_format   = '2BB2B2x5Bx19B8x'
req_trg_param_read_format   = '2BB37x'
req_trg_param_write_format  = '2BB4x7B2x6B2x6B2x6B2x'

rpy_status_format           = '2BB37B'
rpy_sys_monitor_format      = '2BB12B21x4B'
rpy_i2c_read_format         = '2BB2x3B32B'
rpy_get_bitslip_format      = '2BB6x10B6x10B5x'
rpy_get_debug_data_format   = '2BB2B4x31B'
rpy_get_pack_counter_format = '2BB13x24B'
rpy_daq_gen_read_format     = '2BB23B2x4B8x'
rpy_daq_gen2_read_format    = '2BB9Bx19B8x'
rpy_trg_param_read_format   = '2BB4x7B2x6B2x6B2x6B2x'
rpy_trigger_format          = '2BBx32B4x'
rpy_data_format             = '40B'

req_status_code             = 0x00
req_reset_adj_code          = 0x01
req_set_parameters_code     = 0x03
req_sys_monitor_code        = 0x96
req_i2c_read_code           = 0x10
req_i2c_write_code          = 0x11
req_get_bitslip_code        = 0x04
req_set_bitslip_code        = 0x05
req_get_debug_data_code     = 0x0C
req_get_pack_counter_code   = 0x26
req_daq_gen_start_code      = 0x09
req_daq_gen_read_code       = 0x06
req_daq_gen_write_code      = 0x07
req_trg_param_read_code     = 0x0A
req_trg_param_write_code    = 0x0B

rpy_tr0_code                = 0x20
rpy_tr1_code                = 0x21
rpy_tr2_code                = 0x22
rpy_tr3_code                = 0x23
rpy_dq0_code                = 0x24
rpy_dq1_code                = 0x25

uni_chn_to_subblock_list = [
    47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 84, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 1, 2,3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 38, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37
]

subblock_address_dict = {
    "CM_2": 0,
    "CM_3": 1,
    "Channel_36": 2,
    "Channel_37": 3,
    "Channel_38": 4,
    "Channel_39": 5,
    "Channel_40": 6,
    "Channel_41": 7,
    "Channel_42": 8,
    "Channel_43": 9,
    "Channel_44": 10,
    "Channel_45": 11,
    "Channel_46": 12,
    "Channel_47": 13,
    "Channel_48": 14,
    "Channel_49": 15,
    "Channel_50": 16,
    "Channel_51": 17,
    "Channel_52": 18,
    "Channel_53": 19,
    "Channel_54": 20,
    "Channel_55": 21,
    "Channel_56": 22,
    "Channel_57": 23,
    "Channel_58": 24,
    "Channel_59": 25,
    "Channel_60": 26,
    "Channel_61": 27,
    "Channel_62": 28,
    "Channel_63": 29,
    "Channel_64": 30,
    "Channel_65": 31,
    "Channel_66": 32,
    "Channel_67": 33,
    "Channel_68": 34,
    "Channel_69": 35,
    "Channel_70": 36,
    "Channel_71": 37,
    "CALIB_1": 38,

    "Reference_Voltage_1": 40,
    "Global_Analog_1": 41,
    "Master_TDC_1": 42,
    "Digital_Half_1": 43,
    "HalfWise_1": 44,
    "Top": 45,

    "CM_0": 46,
    "CM_1": 47,
    "Channel_0": 48,
    "Channel_1": 49,
    "Channel_2": 50,
    "Channel_3": 51,
    "Channel_4": 52,
    "Channel_5": 53,
    "Channel_6": 54,
    "Channel_7": 55,
    "Channel_8": 56,
    "Channel_9": 57,
    "Channel_10": 58,
    "Channel_11": 59,
    "Channel_12": 60,
    "Channel_13": 61,
    "Channel_14": 62,
    "Channel_15": 63,
    "Channel_16": 64,
    "Channel_17": 65,
    "Channel_18": 66,
    "Channel_19": 67,
    "Channel_20": 68,
    "Channel_21": 69,
    "Channel_22": 70,
    "Channel_23": 71,
    "Channel_24": 72,
    "Channel_25": 73,
    "Channel_26": 74,
    "Channel_27": 75,
    "Channel_28": 76,
    "Channel_29": 77,
    "Channel_30": 78,
    "Channel_31": 79,
    "Channel_32": 80,
    "Channel_33": 81,
    "Channel_34": 82,
    "Channel_35": 83,
    "CALIB_0": 84,

    "Reference_Voltage_0": 86,
    "Global_Analog_0": 87,
    "Master_TDC_0": 88,
    "Digital_Half_0": 89,
    "HalfWise_0": 90
}

def pack_data_req_status(header, fpga_address):
    return struct.pack(req_status_format, header, fpga_address, req_status_code)

def pack_data_req_reset_adj(header, fpga_address, sw_hard_reset_select_7_0, sw_hard_reset, sw_soft_reset_select_7_0, sw_soft_reset, sw_i2c_reset_select_7_0, sw_i2c_reset, reset_pack_counter, adjustable_start):
    if sw_hard_reset > 1 or sw_soft_reset > 1 or sw_i2c_reset > 1:
        print("Invalid reset value")
        return None
    return struct.pack(req_reset_adj_format, header, fpga_address, req_reset_adj_code, sw_hard_reset_select_7_0, sw_hard_reset, sw_soft_reset_select_7_0, sw_soft_reset, sw_i2c_reset_select_7_0, sw_i2c_reset, reset_pack_counter, adjustable_start)

def pack_data_req_set_parameters(header, fpga_address, hv_enable, auto_proto_status, auto_fpga_status, auto_status, auto_i2c_status):
    if hv_enable > 3 or auto_proto_status > 1 or auto_fpga_status > 1 or auto_status > 1 or auto_i2c_status > 1:
        print("Invalid set parameters value")
        return None
    byte7 = (auto_proto_status << 3) | (auto_fpga_status << 2) | (auto_status << 1) | auto_i2c_status
    return struct.pack(req_set_parameters_format, header, fpga_address, req_set_parameters_code, hv_enable, byte7)

def pack_data_req_sys_monitor(header, fpga_address):
    return struct.pack(req_sys_monitor_format, header, fpga_address, req_sys_monitor_code)

def pack_data_req_i2c_read(header, fpga_address, r_wn, length, subaddr_10_3, subaddr_2_0, regaddr_4_0):
    if r_wn > 1 or length > 32 or subaddr_2_0 > 7 or regaddr_4_0 > 31:
        print("Invalid i2c read value")
        return None
    byte5 = (r_wn << 7) | length
    byte7 = (subaddr_2_0 << 5) | regaddr_4_0
    return struct.pack(req_i2c_read_format, header, fpga_address, req_i2c_read_code, byte5, subaddr_10_3, byte7)

def pack_data_req_i2c_write(header, fpga_address, r_wn, length, subaddr_10_3, subaddr_2_0, regaddr_4_0, data):
    if r_wn > 1 or length > 32 or subaddr_2_0 > 7 or regaddr_4_0 > 31:
        print("Invalid i2c write value")
        return None
    if len(data) > 32:
        print("Data length is too long")
        return None
    byte5 = (r_wn << 7) | length
    byte7 = (subaddr_2_0 << 5) | regaddr_4_0
    return struct.pack(req_i2c_write_format, header, fpga_address, req_i2c_write_code, byte5, subaddr_10_3, byte7, *data)

def pack_data_req_get_bitslip(header, fpga_address):
    return struct.pack(req_get_bitslip_format, header, fpga_address, req_get_bitslip_code)

def pack_data_req_set_bitslip(header, fpga_address, io_dly_set_sel, a0_io_dlyo_fclk_10_9, a0_io_dlyo_fcmd_10_9, a0_io_dlyo_fclk_8_1, a0_io_dlyo_fcmd_8_1, a0_io_delay_tr0_8_1, a0_io_delay_tr1_8_1, a0_io_delay_tr2_8_1, a0_io_delay_tr3_8_1, a0_io_delay_dq0_8_1, a0_io_delay_dq1_8_1, a0_io_delay_bit0, a1_io_dlyo_fclk_10_9, a1_io_dlyo_fcmd_10_9, a1_io_dlyo_fclk_8_1, a1_io_dlyo_fcmd_8_1, a1_io_delay_tr0_8_1, a1_io_delay_tr1_8_1, a1_io_delay_tr2_8_1, a1_io_delay_tr3_8_1, a1_io_delay_dq0_8_1, a1_io_delay_dq1_8_1, a1_io_delay_bit0):
    if a0_io_dlyo_fclk_10_9 > 3 or a0_io_dlyo_fcmd_10_9 > 3 or a1_io_dlyo_fclk_10_9 > 3 or a1_io_dlyo_fcmd_10_9 > 3:
        print("Invalid set bitslip value")
        return None
    byte9  = (a0_io_dlyo_fclk_10_9 << 4) | a0_io_dlyo_fcmd_10_9
    byte25 = (a1_io_dlyo_fclk_10_9 << 4) | a1_io_dlyo_fcmd_10_9
    return struct.pack(req_set_bitslip_format, header, fpga_address, req_set_bitslip_code, io_dly_set_sel, byte9, a0_io_dlyo_fclk_8_1, a0_io_dlyo_fcmd_8_1, a0_io_delay_tr0_8_1, a0_io_delay_tr1_8_1, a0_io_delay_tr2_8_1, a0_io_delay_tr3_8_1, a0_io_delay_dq0_8_1, a0_io_delay_dq1_8_1, a0_io_delay_bit0, byte25, a1_io_dlyo_fclk_8_1, a1_io_dlyo_fcmd_8_1, a1_io_delay_tr0_8_1, a1_io_delay_tr1_8_1, a1_io_delay_tr2_8_1, a1_io_delay_tr3_8_1, a1_io_delay_dq0_8_1, a1_io_delay_dq1_8_1, a1_io_delay_bit0)

def pack_data_req_get_debug_data(header, fpga_address):
    return struct.pack(req_get_debug_data_format, header, fpga_address, req_get_debug_data_code)

def pack_data_reg_get_pack_counter(header, fpga_address):
    return struct.pack(req_get_pack_counter_format, header, fpga_address, req_get_pack_counter_code)

def pack_data_req_daq_gen_start(header, fpga_address, daq_push, gen_start_stop, daq_start_stop):
    if gen_start_stop > 1:
        print("Invalid daq gen start value")
        return None
    return struct.pack(req_daq_gen_start_format, header, fpga_address, req_daq_gen_start_code, daq_push, gen_start_stop, daq_start_stop)

def pack_data_req_daq_gen_read(header, fpga_address):
    return struct.pack(req_daq_gen_read_format, header, fpga_address, req_daq_gen_read_code)

def pack_data_req_daq_gen_write(header, fpga_address, data_coll_en, trig_coll_en, daq_fcmd, gen_pre_fcmd, gem_fcmd, ext_trg_en, ext_trg_delay, ext_trg_deadtime, gen_preimp_en, gen_pre_interval, gen_nr_of_cycle, gen_interval, daq_push_fcmd, machine_gun, ext_trg_out_0_len, ext_trg_out_1_len, ext_trg_out_2_len, ext_trg_out_3_len):
    if ext_trg_en > 1 or gen_preimp_en > 1:
        print("Invalid daq gen write value")
        return None
    gen_pre_interval_15_8 = (gen_pre_interval >> 8) & 0xFF
    gen_pre_interval_7_0  = gen_pre_interval & 0xFF
    gen_nr_of_cycle_31_24 = (gen_nr_of_cycle >> 24) & 0xFF
    gen_nr_of_cycle_23_16 = (gen_nr_of_cycle >> 16) & 0xFF
    gen_nr_of_cycle_15_8  = (gen_nr_of_cycle >> 8) & 0xFF
    gen_nr_of_cycle_7_0   = gen_nr_of_cycle & 0xFF
    gen_interval_31_24    = (gen_interval >> 24) & 0xFF
    gen_interval_23_16    = (gen_interval >> 16) & 0xFF
    gen_interval_15_8     = (gen_interval >> 8) & 0xFF
    gen_interval_7_0      = gen_interval & 0xFF
    gen_ext_trg_deadtime_7_0 = ext_trg_deadtime & 0xFF
    gen_ext_trg_deadtime_15_8 = (ext_trg_deadtime >> 8) & 0xFF
    # return struct.pack(req_daq_gen_write_format, header, fpga_address, req_daq_gen_write_code, data_coll_en, trig_coll_en, daq_fcmd, gen_pre_fcmd, gem_fcmd, ext_trg_en, ext_trg_delay, ext_trg_deadtime, gen_preimp_en, gen_pre_interval_15_8, gen_pre_interval_7_0, gen_nr_of_cycle_31_24, gen_nr_of_cycle_23_16, gen_nr_of_cycle_15_8, gen_nr_of_cycle_7_0, gen_interval_31_24, gen_interval_23_16, gen_interval_15_8, gen_interval_7_0, daq_push_fcmd, machine_gun, ext_trg_out_0_len, ext_trg_out_1_len, ext_trg_out_2_len, ext_trg_out_3_len)
    return struct.pack(req_daq_gen2_write_format, header, fpga_address, req_daq_gen_write_code, data_coll_en, trig_coll_en, daq_fcmd, gen_pre_fcmd, gem_fcmd, ext_trg_en, ext_trg_delay, gen_preimp_en, gen_pre_interval_15_8, gen_pre_interval_7_0, gen_nr_of_cycle_31_24, gen_nr_of_cycle_23_16, gen_nr_of_cycle_15_8, gen_nr_of_cycle_7_0, gen_interval_31_24, gen_interval_23_16, gen_interval_15_8, gen_interval_7_0, daq_push_fcmd, machine_gun, gen_ext_trg_deadtime_15_8, gen_ext_trg_deadtime_7_0, ext_trg_out_0_len, ext_trg_out_1_len, ext_trg_out_2_len, ext_trg_out_3_len)
    


def pack_data_req_trg_param_read(header, fpga_address):
    return struct.pack(req_trg_param_read_format, header, fpga_address, req_trg_param_read_code)

def pack_data_reqtrg_param_write(header, fpga_address, trg_tc4, trg_threshold_0_20_16, trg_threshold_0_15_8, trg_threshold_0_7_0, trg_deadtime_0, trg_mask_0_15_8, trg_mask_0_7_0, trg_threshold_1_20_16, trg_threshold_1_15_8, trg_threshold_1_7_0, trg_deadtime_1, trg_mask_1_15_8, trg_mask_1_7_0, trg_threshold_2_20_16, trg_threshold_2_15_8, trg_threshold_2_7_0, trg_deadtime_2, trg_mask_2_15_8, trg_mask_2_7_0, trg_threshold_3_20_16, trg_threshold_3_15_8, trg_threshold_3_7_0, trg_deadtime_3, trg_mask_3_15_8, trg_mask_3_7_0):
    return struct.pack(req_trg_param_write_format, header, fpga_address, req_trg_param_write_code, trg_tc4, trg_threshold_0_20_16, trg_threshold_0_15_8, trg_threshold_0_7_0, trg_deadtime_0, trg_mask_0_15_8, trg_mask_0_7_0, trg_threshold_1_20_16, trg_threshold_1_15_8, trg_threshold_1_7_0, trg_deadtime_1, trg_mask_1_15_8, trg_mask_1_7_0, trg_threshold_2_20_16, trg_threshold_2_15_8, trg_threshold_2_7_0, trg_deadtime_2, trg_mask_2_15_8, trg_mask_2_7_0, trg_threshold_3_20_16, trg_threshold_3_15_8, trg_threshold_3_7_0, trg_deadtime_3, trg_mask_3_15_8, trg_mask_3_7_0)

def unpack_data_rpy_status(data):
    unpacked_data           = struct.unpack(rpy_status_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != req_status_code:
        print("Invalid packet type")
        return None
    
    clk_sel                 = (unpacked_data[3] & 0x04) >> 2
    hv_en                   =  unpacked_data[3] & 0x03
    hw_main_version         =  unpacked_data[4]
    fw_main_version         =  unpacked_data[5]
    base_i2c_running        =  unpacked_data[6] >> 4
    base_i2c_ready          =  unpacked_data[6] & 0x0F
    auto_proto_status       = (unpacked_data[7] & 0x08) >> 3
    auto_fpga_status        = (unpacked_data[7] & 0x04) >> 2
    auto_status             = (unpacked_data[7] & 0x02) >> 1
    auto_i2c_status         =  unpacked_data[7] & 0x01
    i2c_pll                 =  unpacked_data[8]
    i2c_parity              =  unpacked_data[9]
    i2c_error               =  unpacked_data[10]
    i2c_status_top          =  unpacked_data[11]
    i2c_status_sub_l3       =  unpacked_data[12]
    i2c_status_sub_l2       =  unpacked_data[13]
    i2c_status_sub_l1       =  unpacked_data[14]
    i2c_status_sub_l0       =  unpacked_data[15]
    base_i2c_err_cmd_ack_cnt_15_8 = unpacked_data[16]
    base_i2c_err_cmd_ack_cnt_7_0  = unpacked_data[17]
    base_i2c_err_wr_ack_cnt_15_8  = unpacked_data[18]
    base_i2c_err_wr_ack_cnt_7_0   = unpacked_data[19]
    trigger_tc4             =  unpacked_data[20]
    trigger_threshold_20_16 =  unpacked_data[21]
    trigger_threshold_15_8  =  unpacked_data[22]
    trigger_threshold_7_0   =  unpacked_data[23]
    trigger_deadtime        =  unpacked_data[24]
    trigger_mask_15_8       =  unpacked_data[25]
    trigger_mask_7_0        =  unpacked_data[26]
    sgmii_status            =  unpacked_data[27]
    daq_start_stop          =  unpacked_data[28]
    adj_ready               =  unpacked_data[29]
    adj_error               =  unpacked_data[30]
    gen_ready               = (unpacked_data[31] & 0x02) >> 1
    gen_start               =  unpacked_data[31] & 0x01
    gen_cycle_counter_31_24 =  unpacked_data[32]
    gen_cycle_counter_23_16 =  unpacked_data[33]
    gen_cycle_counter_15_8  =  unpacked_data[34]
    gen_cycle_counter_7_0   =  unpacked_data[35]
    ext_trg_en              =  unpacked_data[36] & 0x01
    ext_trg_counter_23_16   =  unpacked_data[37]
    ext_trg_counter_15_8    =  unpacked_data[38]
    ext_trg_counter_7_0     =  unpacked_data[39]

    base_i2c_err_cmd    = (base_i2c_err_cmd_ack_cnt_15_8 << 8) | base_i2c_err_cmd_ack_cnt_7_0
    base_i2c_err_wr     = (base_i2c_err_wr_ack_cnt_15_8 << 8) | base_i2c_err_wr_ack_cnt_7_0
    trigger_threshold   = (trigger_threshold_20_16 << 16) | (trigger_threshold_15_8 << 8) | trigger_threshold_7_0
    trigger_mask        = (trigger_mask_15_8 << 8) | trigger_mask_7_0
    gen_cycle_counter   = (gen_cycle_counter_31_24 << 24) | (gen_cycle_counter_23_16 << 16) | (gen_cycle_counter_15_8 << 8) | gen_cycle_counter_7_0
    ext_trg_counter     = (ext_trg_counter_23_16 << 16) | (ext_trg_counter_15_8 << 8) | ext_trg_counter_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "clk_sel": clk_sel,
        "hv_en": hv_en,
        "hw_main_version": hw_main_version,
        "fw_main_version": fw_main_version,
        "base_i2c_running": base_i2c_running,
        "base_i2c_ready": base_i2c_ready,
        "auto_proto_status": auto_proto_status,
        "auto_fpga_status": auto_fpga_status,
        "auto_status": auto_status,
        "auto_i2c_status": auto_i2c_status,
        "i2c_pll": i2c_pll,
        "i2c_parity": i2c_parity,
        "i2c_error": i2c_error,
        "i2c_status_top": i2c_status_top,
        "i2c_status_sub_l3": i2c_status_sub_l3,
        "i2c_status_sub_l2": i2c_status_sub_l2,
        "i2c_status_sub_l1": i2c_status_sub_l1,
        "i2c_status_sub_l0": i2c_status_sub_l0,
        "base_i2c_err_cmd": base_i2c_err_cmd,
        "base_i2c_err_wr": base_i2c_err_wr,
        "trigger_tc4": trigger_tc4,
        "trigger_threshold": trigger_threshold,
        "trigger_deadtime": trigger_deadtime,
        "trigger_mask": trigger_mask,
        "sgmii_status": sgmii_status,
        "daq_start_stop": daq_start_stop,
        "adj_ready": adj_ready,
        "adj_error": adj_error,
        "gen_ready": gen_ready,
        "gen_start": gen_start,
        "gen_cycle_counter": gen_cycle_counter,
        "ext_trg_en": ext_trg_en,
        "ext_trg_counter": ext_trg_counter
    }

def unpack_data_rpy_sys_monitor(data):
    unpacked_data           = struct.unpack(rpy_sys_monitor_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != req_sys_monitor_code:
        print("Invalid packet type")
        return None
    
    fw_main_version         =  unpacked_data[3]
    fw_sub_version          =  unpacked_data[4]
    fpga_temp_15_8          =  unpacked_data[5]
    fpga_temp_7_0           =  unpacked_data[6]
    fpga_vcc_int_15_8       =  unpacked_data[7]
    fpga_vcc_int_7_0        =  unpacked_data[8]
    fpga_vcc_bram_15_8      =  unpacked_data[9]
    fpga_vcc_bram_7_0       =  unpacked_data[10]
    fpga_vcc_aux_15_8       =  unpacked_data[11]
    fpga_vcc_aux_7_0        =  unpacked_data[12]
    fpga_vcc_o_15_8         =  unpacked_data[13]
    fpga_vcc_o_7_0          =  unpacked_data[14]
    jumbo_enable            =  unpacked_data[15] & 0x01
    number_of_asic          =  unpacked_data[16]
    hw_main_version         =  unpacked_data[17]
    hw_sub_version          =  unpacked_data[18]

    fpga_temp               = (fpga_temp_15_8 << 8) | fpga_temp_7_0
    fpga_vcc_int            = (fpga_vcc_int_15_8 << 8) | fpga_vcc_int_7_0
    fpga_vcc_bram           = (fpga_vcc_bram_15_8 << 8) | fpga_vcc_bram_7_0
    fpga_vcc_aux            = (fpga_vcc_aux_15_8 << 8) | fpga_vcc_aux_7_0
    fpga_vcc_o              = (fpga_vcc_o_15_8 << 8) | fpga_vcc_o_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "fw_main_version": fw_main_version,
        "fw_sub_version": fw_sub_version,
        "fpga_temp": fpga_temp,
        "fpga_vcc_int": fpga_vcc_int,
        "fpga_vcc_bram": fpga_vcc_bram,
        "fpga_vcc_aux": fpga_vcc_aux,
        "fpga_vcc_o": fpga_vcc_o,
        "jumbo_enable": jumbo_enable,
        "number_of_asic": number_of_asic,
        "hw_main_version": hw_main_version,
        "hw_sub_version": hw_sub_version
    }

def unpack_data_rpy_i2c_read(data):
    unpacked_data           = struct.unpack(rpy_i2c_read_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != req_i2c_read_code:
        print("Invalid packet type")
        return None
    
    r_wn                    = (unpacked_data[3] & 0x80) >> 7
    length                  =  unpacked_data[3] & 0x3F
    subaddr_10_3            =  unpacked_data[4]
    subaddr_2_0             = (unpacked_data[5] & 0xE0) >> 5
    regaddr_4_0             =  unpacked_data[5] & 0x1F
    data                    =  unpacked_data[6:]

    subaddr                 = (subaddr_10_3 << 3) | subaddr_2_0
    regaddr                 = regaddr_4_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "r_wn": r_wn,
        "length": length,
        "subaddr": subaddr,
        "regaddr": regaddr,
        "data": data
    }

def unpack_data_rpy_get_bitslip(data):
    unpacked_data           = struct.unpack(rpy_get_bitslip_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != req_get_bitslip_code:
        print("Invalid packet type")
        return None
    
    a0_io_dlyo_fclk_10_9      = (unpacked_data[3] & 0x30) >> 4
    a0_io_dlyo_fcmd_10_9      =  unpacked_data[3] & 0x03
    a0_io_dlyo_fclk_8_1       =  unpacked_data[4]
    a0_io_dlyo_fcmd_8_1       =  unpacked_data[5]
    a0_io_delay_tr0_8_1       =  unpacked_data[6]
    a0_io_delay_tr1_8_1       =  unpacked_data[7]
    a0_io_delay_tr2_8_1       =  unpacked_data[8]
    a0_io_delay_tr3_8_1       =  unpacked_data[9]
    a0_io_delay_dq0_8_1       =  unpacked_data[10]
    a0_io_delay_dq1_8_1       =  unpacked_data[11]
    a0_io_delay_bit0          =  unpacked_data[12]

    a1_io_dlyo_fclk_10_9      = (unpacked_data[13] & 0x30) >> 4
    a1_io_dlyo_fcmd_10_9      =  unpacked_data[13] & 0x03
    a1_io_dlyo_fclk_8_1       =  unpacked_data[14]
    a1_io_dlyo_fcmd_8_1       =  unpacked_data[15]
    a1_io_delay_tr0_8_1       =  unpacked_data[16]
    a1_io_delay_tr1_8_1       =  unpacked_data[17]
    a1_io_delay_tr2_8_1       =  unpacked_data[18]
    a1_io_delay_tr3_8_1       =  unpacked_data[19]
    a1_io_delay_dq0_8_1       =  unpacked_data[20]
    a1_io_delay_dq1_8_1       =  unpacked_data[21]
    a1_io_delay_bit0          =  unpacked_data[22]

    a0_io_dlyo_fclk          = (a0_io_dlyo_fclk_10_9 << 9) | (a0_io_dlyo_fclk_8_1 << 1) | (a0_io_delay_bit0 >> 7) & 0x01
    a0_io_dlyo_fcmd          = (a0_io_dlyo_fcmd_10_9 << 9) | (a0_io_dlyo_fcmd_8_1 << 1) | (a0_io_delay_bit0 >> 6) & 0x01
    a0_io_delay_tr0          = (a0_io_delay_tr0_8_1 << 1) | (a0_io_delay_bit0 >> 5) & 0x01
    a0_io_delay_tr1          = (a0_io_delay_tr1_8_1 << 1) | (a0_io_delay_bit0 >> 4) & 0x01
    a0_io_delay_tr2          = (a0_io_delay_tr2_8_1 << 1) | (a0_io_delay_bit0 >> 3) & 0x01
    a0_io_delay_tr3          = (a0_io_delay_tr3_8_1 << 1) | (a0_io_delay_bit0 >> 2) & 0x01
    a0_io_delay_dq0          = (a0_io_delay_dq0_8_1 << 1) | (a0_io_delay_bit0 >> 1) & 0x01
    a0_io_delay_dq1          = (a0_io_delay_dq1_8_1 << 1) | a0_io_delay_bit0 & 0x01
    a1_io_dlyo_fclk          = (a1_io_dlyo_fclk_10_9 << 9) | (a1_io_dlyo_fclk_8_1 << 1) | (a1_io_delay_bit0 >> 7) & 0x01
    a1_io_dlyo_fcmd          = (a1_io_dlyo_fcmd_10_9 << 9) | (a1_io_dlyo_fcmd_8_1 << 1) | (a1_io_delay_bit0 >> 6) & 0x01
    a1_io_delay_tr0          = (a1_io_delay_tr0_8_1 << 1) | (a1_io_delay_bit0 >> 5) & 0x01
    a1_io_delay_tr1          = (a1_io_delay_tr1_8_1 << 1) | (a1_io_delay_bit0 >> 4) & 0x01
    a1_io_delay_tr2          = (a1_io_delay_tr2_8_1 << 1) | (a1_io_delay_bit0 >> 3) & 0x01
    a1_io_delay_tr3          = (a1_io_delay_tr3_8_1 << 1) | (a1_io_delay_bit0 >> 2) & 0x01
    a1_io_delay_dq0          = (a1_io_delay_dq0_8_1 << 1) | (a1_io_delay_bit0 >> 1) & 0x01
    a1_io_delay_dq1          = (a1_io_delay_dq1_8_1 << 1) | a1_io_delay_bit0 & 0x01

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "a0_io_dlyo_fclk": a0_io_dlyo_fclk,
        "a0_io_dlyo_fcmd": a0_io_dlyo_fcmd,
        "a0_io_delay_tr0": a0_io_delay_tr0,
        "a0_io_delay_tr1": a0_io_delay_tr1,
        "a0_io_delay_tr2": a0_io_delay_tr2,
        "a0_io_delay_tr3": a0_io_delay_tr3,
        "a0_io_delay_dq0": a0_io_delay_dq0,
        "a0_io_delay_dq1": a0_io_delay_dq1,
        "a1_io_dlyo_fclk": a1_io_dlyo_fclk,
        "a1_io_dlyo_fcmd": a1_io_dlyo_fcmd,
        "a1_io_delay_tr0": a1_io_delay_tr0,
        "a1_io_delay_tr1": a1_io_delay_tr1,
        "a1_io_delay_tr2": a1_io_delay_tr2,
        "a1_io_delay_tr3": a1_io_delay_tr3,
        "a1_io_delay_dq0": a1_io_delay_dq0,
        "a1_io_delay_dq1": a1_io_delay_dq1
    }

def unpack_data_rpy_get_debug_data(data):
    unpacked_data           = struct.unpack(rpy_get_debug_data_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != req_get_debug_data_code:
        print("Invalid packet type")
        return None
    
    bx_counter_11_8         =  unpacked_data[3] & 0x0F
    bx_counter_7_0          =  unpacked_data[4]
    s_io_dlyo_daq1_8_1      =  unpacked_data[5]
    s_io_dlyo_daq0_8_1      =  unpacked_data[6]
    adj_ready               =  unpacked_data[7] & 0x3F
    adj_dq1                 = (unpacked_data[8] & 0x38) >> 3
    adj_dq0                 =  unpacked_data[8] & 0x07
    adj_tr3                 = (unpacked_data[9] & 0x38) >> 3
    adj_tr2                 =  unpacked_data[9] & 0x07
    adj_tr1                 = (unpacked_data[10] & 0x38) >> 3
    adj_tr0                 =  unpacked_data[10] & 0x07
    adj_error               =  unpacked_data[11] & 0x3F
    trg0_value_31_24        =  unpacked_data[12]
    trg0_value_23_16        =  unpacked_data[13]
    trg0_value_15_8         =  unpacked_data[14]
    trg0_value_7_0          =  unpacked_data[15]
    trg1_value_31_24        =  unpacked_data[16]
    trg1_value_23_16        =  unpacked_data[17]
    trg1_value_15_8         =  unpacked_data[18]
    trg1_value_7_0          =  unpacked_data[19]
    trg2_value_31_24        =  unpacked_data[20]
    trg2_value_23_16        =  unpacked_data[21]
    trg2_value_15_8         =  unpacked_data[22]
    trg2_value_7_0          =  unpacked_data[23]
    trg3_value_31_24        =  unpacked_data[24]
    trg3_value_23_16        =  unpacked_data[25]
    trg3_value_15_8         =  unpacked_data[26]
    trg3_value_7_0          =  unpacked_data[27]
    data0_value_31_24       =  unpacked_data[28]
    data0_value_23_16       =  unpacked_data[29]
    data0_value_15_8        =  unpacked_data[30]
    data0_value_7_0         =  unpacked_data[31]
    data1_value_31_24       =  unpacked_data[32]
    data1_value_23_16       =  unpacked_data[33]
    data1_value_15_8        =  unpacked_data[34]
    data1_value_7_0         =  unpacked_data[35]

    bx_counter              = (bx_counter_11_8 << 8) | bx_counter_7_0
    trg0_value              = (trg0_value_31_24 << 24) | (trg0_value_23_16 << 16) | (trg0_value_15_8 << 8) | trg0_value_7_0
    trg1_value              = (trg1_value_31_24 << 24) | (trg1_value_23_16 << 16) | (trg1_value_15_8 << 8) | trg1_value_7_0
    trg2_value              = (trg2_value_31_24 << 24) | (trg2_value_23_16 << 16) | (trg2_value_15_8 << 8) | trg2_value_7_0
    trg3_value              = (trg3_value_31_24 << 24) | (trg3_value_23_16 << 16) | (trg3_value_15_8 << 8) | trg3_value_7_0
    data0_value             = (data0_value_31_24 << 24) | (data0_value_23_16 << 16) | (data0_value_15_8 << 8) | data0_value_7_0
    data1_value             = (data1_value_31_24 << 24) | (data1_value_23_16 << 16) | (data1_value_15_8 << 8) | data1_value_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "bx_counter": bx_counter,
        "s_io_dlyo_daq1": s_io_dlyo_daq1_8_1,
        "s_io_dlyo_daq0": s_io_dlyo_daq0_8_1,
        "adj_ready": adj_ready,
        "adj_dq1": adj_dq1,
        "adj_dq0": adj_dq0,
        "adj_tr3": adj_tr3,
        "adj_tr2": adj_tr2,
        "adj_tr1": adj_tr1,
        "adj_tr0": adj_tr0,
        "adj_error": adj_error,
        "trg0_value": trg0_value,
        "trg1_value": trg1_value,
        "trg2_value": trg2_value,
        "trg3_value": trg3_value,
        "data0_value": data0_value,
        "data1_value": data1_value
    }

def unpack_data_rpy_get_pack_counter(data):
    unpacked_data           = struct.unpack(rpy_get_pack_counter_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != req_get_pack_counter_code:
        print("Invalid packet type")
        return None
    
    data_packet_counter_asic0_23_16 = unpacked_data[3]
    data_packet_counter_asic0_15_8  = unpacked_data[4]
    data_packet_counter_asic0_7_0   = unpacked_data[5]
    data_packet_counter_asic1_23_16 = unpacked_data[6]
    data_packet_counter_asic1_15_8  = unpacked_data[7]
    data_packet_counter_asic1_7_0   = unpacked_data[8]
    data_packet_counter_asic2_23_16 = unpacked_data[9]
    data_packet_counter_asic2_15_8  = unpacked_data[10]
    data_packet_counter_asic2_7_0   = unpacked_data[11]
    data_packet_counter_asic3_23_16 = unpacked_data[12]
    data_packet_counter_asic3_15_8  = unpacked_data[13]
    data_packet_counter_asic3_7_0   = unpacked_data[14]
    data_packet_counter_asic4_23_16 = unpacked_data[15]
    data_packet_counter_asic4_15_8  = unpacked_data[16]
    data_packet_counter_asic4_7_0   = unpacked_data[17]
    data_packet_counter_asic5_23_16 = unpacked_data[18]
    data_packet_counter_asic5_15_8  = unpacked_data[19]
    data_packet_counter_asic5_7_0   = unpacked_data[20]
    data_packet_counter_asic6_23_16 = unpacked_data[21]
    data_packet_counter_asic6_15_8  = unpacked_data[22]
    data_packet_counter_asic6_7_0   = unpacked_data[23]
    data_packet_counter_asic7_23_16 = unpacked_data[24]
    data_packet_counter_asic7_15_8  = unpacked_data[25]
    data_packet_counter_asic7_7_0   = unpacked_data[26]

    data_packet_counter_asic0 = (data_packet_counter_asic0_23_16 << 16) | (data_packet_counter_asic0_15_8 << 8) | data_packet_counter_asic0_7_0
    data_packet_counter_asic1 = (data_packet_counter_asic1_23_16 << 16) | (data_packet_counter_asic1_15_8 << 8) | data_packet_counter_asic1_7_0
    data_packet_counter_asic2 = (data_packet_counter_asic2_23_16 << 16) | (data_packet_counter_asic2_15_8 << 8) | data_packet_counter_asic2_7_0
    data_packet_counter_asic3 = (data_packet_counter_asic3_23_16 << 16) | (data_packet_counter_asic3_15_8 << 8) | data_packet_counter_asic3_7_0
    data_packet_counter_asic4 = (data_packet_counter_asic4_23_16 << 16) | (data_packet_counter_asic4_15_8 << 8) | data_packet_counter_asic4_7_0
    data_packet_counter_asic5 = (data_packet_counter_asic5_23_16 << 16) | (data_packet_counter_asic5_15_8 << 8) | data_packet_counter_asic5_7_0
    data_packet_counter_asic6 = (data_packet_counter_asic6_23_16 << 16) | (data_packet_counter_asic6_15_8 << 8) | data_packet_counter_asic6_7_0
    data_packet_counter_asic7 = (data_packet_counter_asic7_23_16 << 16) | (data_packet_counter_asic7_15_8 << 8) | data_packet_counter_asic7_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "data_packet_counter_asic0": data_packet_counter_asic0,
        "data_packet_counter_asic1": data_packet_counter_asic1,
        "data_packet_counter_asic2": data_packet_counter_asic2,
        "data_packet_counter_asic3": data_packet_counter_asic3,
        "data_packet_counter_asic4": data_packet_counter_asic4,
        "data_packet_counter_asic5": data_packet_counter_asic5,
        "data_packet_counter_asic6": data_packet_counter_asic6,
        "data_packet_counter_asic7": data_packet_counter_asic7
    }

def unpack_data_rpy_rpy_daq_gen_read(data):
    unpacked_data          = struct.unpack(rpy_daq_gen2_read_format, data)
    header                 = unpacked_data[0]
    fpga_address           = unpacked_data[1]
    packet_type            = unpacked_data[2]
    if packet_type != req_daq_gen_read_code:
        print("Invalid packet type")
        return None
    
    data_coll_en           = unpacked_data[3]
    trig_coll_en           = unpacked_data[4]
    gen_start_stop         = unpacked_data[5] & 0x01
    daq_start_stop         = unpacked_data[6]
    daq_fcmd               = unpacked_data[7]
    gen_pre_fcmd           = unpacked_data[8]
    gem_fcmd               = unpacked_data[9]
    ext_trg_en             = unpacked_data[10] & 0x01
    ext_trg_delay          = unpacked_data[11]
    # ext_trg_deadtime       = unpacked_data[11]
    gen_preimp_en          = unpacked_data[12] & 0x01
    gen_pre_interval_15_8  = unpacked_data[13]
    gen_pre_interval_7_0   = unpacked_data[14]
    gen_nr_of_cycle_31_24  = unpacked_data[15]
    gen_nr_of_cycle_23_16  = unpacked_data[16]
    gen_nr_of_cycle_15_8   = unpacked_data[17]
    gen_nr_of_cycle_7_0    = unpacked_data[18]
    gen_interval_31_24     = unpacked_data[19]
    gen_interval_23_16     = unpacked_data[20]
    gen_interval_15_8      = unpacked_data[21]
    gen_interval_7_0       = unpacked_data[22]
    daq_push_fcmd          = unpacked_data[23]
    machine_gun            = unpacked_data[24]
    ext_trg_deadtime_15_8  = unpacked_data[25]
    ext_trg_deadtime_7_0   = unpacked_data[26]
    ext_trg_out_0_len      = unpacked_data[27]
    ext_trg_out_1_len      = unpacked_data[28]
    ext_trg_out_2_len      = unpacked_data[29]
    ext_trg_out_3_len      = unpacked_data[30]

    gen_pre_interval       = (gen_pre_interval_15_8 << 8) | gen_pre_interval_7_0
    gen_nr_of_cycle        = (gen_nr_of_cycle_31_24 << 24) | (gen_nr_of_cycle_23_16 << 16) | (gen_nr_of_cycle_15_8 << 8) | gen_nr_of_cycle_7_0
    gen_interval           = (gen_interval_31_24 << 24) | (gen_interval_23_16 << 16) | (gen_interval_15_8 << 8) | gen_interval_7_0
    ext_trg_deadtime       = (ext_trg_deadtime_15_8 << 8) | ext_trg_deadtime_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "data_coll_en": data_coll_en,
        "trig_coll_en": trig_coll_en,
        "gen_start_stop": gen_start_stop,
        "daq_start_stop": daq_start_stop,
        "daq_fcmd": daq_fcmd,
        "gen_pre_fcmd": gen_pre_fcmd,
        "gem_fcmd": gem_fcmd,
        "ext_trg_en": ext_trg_en,
        "ext_trg_delay": ext_trg_delay,
        "ext_trg_deadtime": ext_trg_deadtime,
        "gen_preimp_en": gen_preimp_en,
        "gen_pre_interval": gen_pre_interval,
        "gen_nr_of_cycle": gen_nr_of_cycle,
        "gen_interval": gen_interval,
        "daq_push_fcmd": daq_push_fcmd,
        "machine_gun": machine_gun,
        "ext_trg_out_0_len": ext_trg_out_0_len,
        "ext_trg_out_1_len": ext_trg_out_1_len,
        "ext_trg_out_2_len": ext_trg_out_2_len,
        "ext_trg_out_3_len": ext_trg_out_3_len
    }

def unpack_data_rpy_trg_param_read(data):
    unpacked_data           = struct.unpack(rpy_trg_param_read_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != req_trg_param_read_code:
        print("Invalid packet type")
        return None
    
    trigger_tc4             =  unpacked_data[3]
    a0_trigger_threshold_20_16 =  unpacked_data[4] & 0x1F
    a0_trigger_threshold_15_8  =  unpacked_data[5]
    a0_trigger_threshold_7_0   =  unpacked_data[6]
    a0_trigger_deadtime        =  unpacked_data[7]
    a0_trigger_mask_15_8       =  unpacked_data[8]
    a0_trigger_mask_7_0        =  unpacked_data[9]
    a1_trigger_threshold_20_16 =  unpacked_data[10] & 0x1F
    a1_trigger_threshold_15_8  =  unpacked_data[11]
    a1_trigger_threshold_7_0   =  unpacked_data[12]
    a1_trigger_deadtime        =  unpacked_data[13]
    a1_trigger_mask_15_8       =  unpacked_data[14]
    a1_trigger_mask_7_0        =  unpacked_data[15]
    a2_trigger_threshold_20_16 =  unpacked_data[16] & 0x1F
    a2_trigger_threshold_15_8  =  unpacked_data[17]
    a2_trigger_threshold_7_0   =  unpacked_data[18]
    a2_trigger_deadtime        =  unpacked_data[19]
    a2_trigger_mask_15_8       =  unpacked_data[20]
    a2_trigger_mask_7_0        =  unpacked_data[21]
    a3_trigger_threshold_20_16 =  unpacked_data[22] & 0x1F
    a3_trigger_threshold_15_8  =  unpacked_data[23]
    a3_trigger_threshold_7_0   =  unpacked_data[24]
    a3_trigger_deadtime        =  unpacked_data[25]
    a3_trigger_mask_15_8       =  unpacked_data[26]
    a3_trigger_mask_7_0        =  unpacked_data[27]

    a0_trigger_threshold       = (a0_trigger_threshold_20_16 << 16) | (a0_trigger_threshold_15_8 << 8) | a0_trigger_threshold_7_0
    a0_trigger_mask            = (a0_trigger_mask_15_8 << 8) | a0_trigger_mask_7_0
    a1_trigger_threshold       = (a1_trigger_threshold_20_16 << 16) | (a1_trigger_threshold_15_8 << 8) | a1_trigger_threshold_7_0
    a1_trigger_mask            = (a1_trigger_mask_15_8 << 8) | a1_trigger_mask_7_0
    a2_trigger_threshold       = (a2_trigger_threshold_20_16 << 16) | (a2_trigger_threshold_15_8 << 8) | a2_trigger_threshold_7_0
    a2_trigger_mask            = (a2_trigger_mask_15_8 << 8) | a2_trigger_mask_7_0
    a3_trigger_threshold       = (a3_trigger_threshold_20_16 << 16) | (a3_trigger_threshold_15_8 << 8) | a3_trigger_threshold_7_0
    a3_trigger_mask            = (a3_trigger_mask_15_8 << 8) | a3_trigger_mask_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "trigger_tc4": trigger_tc4,
        "a0_trigger_threshold": a0_trigger_threshold,
        "a0_trigger_deadtime": a0_trigger_deadtime,
        "a0_trigger_mask": a0_trigger_mask,
        "a1_trigger_threshold": a1_trigger_threshold,
        "a1_trigger_deadtime": a1_trigger_deadtime,
        "a1_trigger_mask": a1_trigger_mask,
        "a2_trigger_threshold": a2_trigger_threshold,
        "a2_trigger_deadtime": a2_trigger_deadtime,
        "a2_trigger_mask": a2_trigger_mask,
        "a3_trigger_threshold": a3_trigger_threshold,
        "a3_trigger_deadtime": a3_trigger_deadtime,
        "a3_trigger_mask": a3_trigger_mask
    }

def unpack_data_rpy_trigger(data):
    unpacked_data           = struct.unpack(rpy_trigger_format, data)
    header                  =  unpacked_data[0]
    fpga_address            =  unpacked_data[1]
    packet_type             =  unpacked_data[2]
    if packet_type != rpy_tr0_code and packet_type != rpy_tr1_code and packet_type != rpy_tr2_code and packet_type != rpy_tr3_code:
        print("Invalid packet type")
        return None
    
    timestamp_29_24         =  unpacked_data[3] & 0x3F
    timestamp_23_16         =  unpacked_data[4]
    timestamp_15_8          =  unpacked_data[5]
    timestamp_7_0           =  unpacked_data[6]
    trigger_data_m3_31_24   =  unpacked_data[7]
    trigger_data_m3_23_16   =  unpacked_data[8]
    trigger_data_m3_15_8    =  unpacked_data[9]
    trigger_data_m3_7_0     =  unpacked_data[10]
    trigger_data_m2_31_24   =  unpacked_data[11]
    trigger_data_m2_23_16   =  unpacked_data[12]
    trigger_data_m2_15_8    =  unpacked_data[13]
    trigger_data_m2_7_0     =  unpacked_data[14]
    trigger_data_m1_31_24   =  unpacked_data[15]
    trigger_data_m1_23_16   =  unpacked_data[16]
    trigger_data_m1_15_8    =  unpacked_data[17]
    trigger_data_m1_7_0     =  unpacked_data[18]
    trigger_data_0_31_24    =  unpacked_data[19]
    trigger_data_0_23_16    =  unpacked_data[20]
    trigger_data_0_15_8     =  unpacked_data[21]
    trigger_data_0_7_0      =  unpacked_data[22]
    trigger_data_1_31_24    =  unpacked_data[23]
    trigger_data_1_23_16    =  unpacked_data[24]
    trigger_data_1_15_8     =  unpacked_data[25]
    trigger_data_1_7_0      =  unpacked_data[26]
    trigger_data_2_31_24    =  unpacked_data[27]
    trigger_data_2_23_16    =  unpacked_data[28]
    trigger_data_2_15_8     =  unpacked_data[29]
    trigger_data_2_7_0      =  unpacked_data[30]
    trigger_data_3_31_24    =  unpacked_data[31]
    trigger_data_3_23_16    =  unpacked_data[32]
    trigger_data_3_15_8     =  unpacked_data[33]
    trigger_data_3_7_0      =  unpacked_data[34]

    timestamp               = (timestamp_29_24 << 24) | (timestamp_23_16 << 16) | (timestamp_15_8 << 8) | timestamp_7_0
    trigger_data_m3         = (trigger_data_m3_31_24 << 24) | (trigger_data_m3_23_16 << 16) | (trigger_data_m3_15_8 << 8) | trigger_data_m3_7_0
    trigger_data_m2         = (trigger_data_m2_31_24 << 24) | (trigger_data_m2_23_16 << 16) | (trigger_data_m2_15_8 << 8) | trigger_data_m2_7_0
    trigger_data_m1         = (trigger_data_m1_31_24 << 24) | (trigger_data_m1_23_16 << 16) | (trigger_data_m1_15_8 << 8) | trigger_data_m1_7_0
    trigger_data_0          = (trigger_data_0_31_24 << 24) | (trigger_data_0_23_16 << 16) | (trigger_data_0_15_8 << 8) | trigger_data_0_7_0
    trigger_data_1          = (trigger_data_1_31_24 << 24) | (trigger_data_1_23_16 << 16) | (trigger_data_1_15_8 << 8) | trigger_data_1_7_0
    trigger_data_2          = (trigger_data_2_31_24 << 24) | (trigger_data_2_23_16 << 16) | (trigger_data_2_15_8 << 8) | trigger_data_2_7_0
    trigger_data_3          = (trigger_data_3_31_24 << 24) | (trigger_data_3_23_16 << 16) | (trigger_data_3_15_8 << 8) | trigger_data_3_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "timestamp": timestamp,
        "trigger_data_m3": trigger_data_m3,
        "trigger_data_m2": trigger_data_m2,
        "trigger_data_m1": trigger_data_m1,
        "trigger_data_0": trigger_data_0,
        "trigger_data_1": trigger_data_1,
        "trigger_data_2": trigger_data_2,
        "trigger_data_3": trigger_data_3
    }

def unpack_data_rpy_data(data):
    unpacked_data = struct.unpack(rpy_data_format, data)
    header = unpacked_data[0]
    fpga_address = unpacked_data[1]
    packet_type = unpacked_data[2]
    if packet_type != rpy_dq0_code and packet_type != rpy_dq1_code:
        print("Invalid packet type")
        return None
    
    package_id = unpacked_data[3]
    timestamp_29_24 = unpacked_data[4] & 0x3F
    timestamp_23_16 = unpacked_data[5]
    timestamp_15_8 = unpacked_data[6]
    timestamp_7_0 = unpacked_data[7]
    data = unpacked_data[8:]

    timestamp = (timestamp_29_24 << 24) | (timestamp_23_16 << 16) | (timestamp_15_8 << 8) | timestamp_7_0

    return {
        "header": header,
        "fpga_address": fpga_address,
        "packet_type": packet_type,
        "package_id": package_id,
        "timestamp": timestamp,
        "data": data
    }
import serial
import struct
import time
import datetime

cmd_get_version = 0x01
cmd_get_config = 0x02
cmd_set_config = 0x04
cmd_set_serial = 0x06
cmd_init_device = 0x07
cmd_read_init_device = 0x08
cmd_set_channel = 0x09
cmd_get_channel = 0x0A
cmd_set_sleep = 0x0B
cmd_get_sleep = 0x0C
cmd_get_sysversion = 0x0d
cmd_wakeup_tx = 0x0e
cmd_setwkup_code = 0x10
cmd_getwkup_code = 0x11
cmd_start_logging = 0x12
cmd_stop_logging = 0x13
cmd_led_op = 0x14
cmd_radio_pv = 0x15,
cmd_set_code_date = 0x16
cmd_get_uid = 0x17

console_raw_sof = 0x02
console_raw_eof = 0x03

led_red = 1
led_green = 2
led_yellow = 3

led_op_on = 1
led_op_off = 0

mfg_valid = 0x7068797a

# Raw message format
# sof,pkt_len,cmd <data> eof

def make_cmd(cmd,data):
    sbuf = struct.pack('b',console_raw_sof)
     # data is expected to be already packe.
    buf = struct.pack('b',cmd)+data.encode('utf-8')
    lbuf = struct.pack('h',len(buf))
    pkt = sbuf +lbuf+buf+struct.pack('b',console_raw_eof)
    return pkt

def to_bcd(instr):
    num = 0
    for a in instr:
        if a in '0123456789':
            num = (num << 4) | (ord(a)-ord('0'))
    return num

def get_today():
    now = datetime.datetime.now()
    mmddyy = str(now.month)+str(now.day)+str(now.year-2000)
    enc_mmddyy = to_bcd(mmddyy)
    print(hex(enc_mmddyy))
    return enc_mmddyy

def get_tomorrow():
    now = datetime.datetime.now()
    mmddyy = str(now.month)+str(now.day+1)+str(now.year-2000)
    enc_mmddyy = to_bcd(mmddyy)
    print(hex(enc_mmddyy))
    return enc_mmddyy

# bcd date to string.
def bcd_date_to_str(dt):
    sdt = hex(dt)[2:]
    sdt = '0'*(6-len(sdt))+sdt
    dstr = sdt[:2]+'/'+sdt[2:4]+'/'+sdt[4:]
    return dstr

def do_get_config(prt):
    get_cfg = make_cmd(cmd_get_config,'')
    prt.write(get_cfg)
    time.sleep(0.5)
    rsp = prt.read(100)
    print(rsp)
    flds = struct.unpack('<BHBLLLLBBBBB',rsp)
    valid = flds[3]
    sercode = flds[4]
    mfg_date = flds[5]
    code_date = flds[6]
    chnl = flds[7]
    slptm = flds[8]
    wkup = flds[9]

    if valid == mfg_valid:
        print("Serial:{0}, Mfg:{1}, Code:{2}, Channel:{3}".format(hex(sercode)[2:],
                                                                  bcd_date_to_str(mfg_date),
                                                                  bcd_date_to_str(code_date),
                                                                  hex(chnl)[2:]))
        return hex(sercode)[2:],bcd_date_to_str(mfg_date),bcd_date_to_str(code_date),hex(chnl)[2:]
    else:
        return 'error','error','error'
    

def do_update_channel(prt,chnl):
    chnlstr = struct.pack('<B',chnl)
    chnl_upd = make_cmd(cmd_set_channel,chnlstr.decode('utf-8'))
    prt.write(chnl_upd)
    time.sleep(0.5)
    rsp = prt.read(100)
    if len(rsp):
        print("Channel updated")
    else:
        print ("Error updating channel.")

def do_code_date_update(prt):
    code_date = struct.pack('<L',get_today())
    cd_upd = make_cmd(cmd_set_code_date, code_date.decode('utf-8'))
    prt.write(cd_upd)
    time.sleep(0.5)
    rsp = prt.read(100)
    if len(rsp):
        print("Code date updated.")
    else:
        print ("Error update code date")
    
# config structure is
# 4 bytes valid 0x7068797A (phyz)
# 4 bytes serial number -
# 4 bytes mfg_date
# these 12 bytes should not be updated. 
# dates are BCD coded with MMDDYY
# 4 bytes code_date - this needs to be updated every time code is updated.
# 1 byte channel number
# 1 byte sleep time
# 1 byte wakeup code - Wake up code and sleep time is not used and set to 0x1020

def do_set_mfg_config(prt):
    valid = mfg_valid
    # serial code should be generated from a database.
    # right now it is hardcoded, but eventually needs
    # to be accessed and stored remotely along with
    # the device uid.
    sercode = 0x01000001
    mfg_date = get_today()
    code_date = get_today()
    chnl = 0x01
    slptm = 0x10
    wkup = 0x20

    cfginfo = struct.pack('<LLLLBBB',valid,sercode,mfg_date,code_date,chnl,slptm,wkup)
    cfgcmd = make_cmd(cmd_set_config,cfginfo.decode('utf-8'))
    prt.write(cfgcmd)
    time.sleep(0.5)
    rsp = prt.read(100)
    if len(rsp):
        print("Configuration updated.")
    else:
        print("Error setting manufacture data.")

def pad_zero(olen,istr):
    num_to_pad = olen-len(istr)
    pads = '0'*num_to_pad
    return pads+istr

def do_get_radio_part_version(prt,radio):
    radio_str = struct.pack('<B',radio)
    radio_part_cmd = make_cmd(cmd_radio_pv, radio_str.decode('utf-8'))
    prt.write(radio_part_cmd)
    time.sleep(1)
    rsp = prt.read(100)
    if len(rsp):
        pkt = struct.unpack('<BHBBBBB',rsp)
        print("Radio: {0} Part: {1} Version: {2}".format(pkt[3],hex(pkt[4]),hex(pkt[5])))
        return pkt[4],pkt[5]
    else:
        print("No response for radio command.")
        return 0x00,0x00

def do_get_uid(prt):
    get_uid_cmd = make_cmd(cmd_get_uid,'')
    prt.write(get_uid_cmd)
    time.sleep(0.5)
    rsp = prt.read(100)
    if len(rsp):
        pkt = struct.unpack('<BHBLLLB',rsp)
        print("UID MH: {0} UID ML: {1} UID L: {2}".format(hex(pkt[3]),hex(pkt[4]),hex(pkt[5])))
        return pkt[3],pkt[4],pkt[5]
    else:
        return 0,0,0

def do_led_ops(prt):
    led_red_on = struct.pack('<BB',led_red,led_op_on)
    led_red_off = struct.pack('<BB',led_red,led_op_off)
    led_green_on = struct.pack('<BB',led_green,led_op_on)
    led_green_off = struct.pack('<BB',led_green,led_op_off)
    led_yellow_on = struct.pack('<BB',led_yellow,led_op_on)
    led_yellow_off = struct.pack('<BB',led_yellow,led_op_off)        
    led_red_on = make_cmd(cmd_led_op,led_red_on.decode('utf-8'))
    led_red_off = make_cmd(cmd_led_op,led_red_off.decode('utf-8'))
    led_green_on = make_cmd(cmd_led_op,led_green_on.decode('utf-8'))
    led_green_off = make_cmd(cmd_led_op,led_green_off.decode('utf-8'))
    led_yellow_on = make_cmd(cmd_led_op,led_yellow_on.decode('utf-8'))
    led_yellow_off = make_cmd(cmd_led_op,led_yellow_off.decode('utf-8'))
    prt.write(led_red_on)
    time.sleep(1)
    prt.write(led_red_off)
    time.sleep(1)
    prt.write(led_green_on)
    time.sleep(1)
    prt.write(led_green_off)
    time.sleep(1)
    prt.write(led_yellow_on)
    time.sleep(1)
    prt.write(led_yellow_off)
    time.sleep(1)
    prt.write(led_red_on)
    
def do_get_version(prt):
    get_vers = make_cmd(cmd_get_version,'')
    prt.write(get_vers)
    rsp = prt.read(100)
    if len(rsp):
        print(rsp,len(rsp))
        vers = struct.unpack('<BHBHHB',rsp)
        hwver = pad_zero(4,hex(vers[2])[2:])
        fwver = pad_zero(4,hex(vers[3])[2:])
        hwver = hwver[:2]+'.'+hwver[2:]
        fwver = fwver[:2]+'.'+fwver[2:]
        print("HW Version: {0}, FW Version: {1}".format(hwver,fwver))
        return hwver, fwver
    else:
        print("Empty response.")
        return 'error','error'

def send_logger_on(prt):
    log_on = make_cmd(cmd_start_logging,'')
    print(log_on)
    prt.write(log_on)

def send_logger_off(prt):
    log_off = make_cmd(cmd_stop_logging,'')
    print(log_off)
    prt.write(log_off)

def set_to_raw(prt):
    prt.write("raw\r\n".encode('utf-8'))
    
def open_serial(com):
    prt = serial.Serial(com,3000000,timeout=0.1)
    return prt

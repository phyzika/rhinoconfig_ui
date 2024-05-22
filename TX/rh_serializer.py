#
# rhino serializer.
# Write serial number to boards along with version number
# manufactre date and configuration date.
# This will not be supplied to the calender and will be used only
# for internal purposes.
# verson 0.3
import serial
import serial
from serial.tools import list_ports
import struct
import socket
import signal
import sys
import sqlite3
import time

brate = 921600
get_version = 0x01
get_config = 0x02
set_config = 0x04
set_serial = 0x06
get_adxl_info = 0x11
set_adxl_info = 0x12
pause_sleep = 0x13

sf = 0x02
ef = 0x03
cfg_rsp = '<BBBBBBBBBBBBBBBBBBBBBBB'

db_conn = sqlite3.connect('rh_cfg.db')
                        

# set version
# Pass the serial number.
# 
def do_set_version(sport,snum,fw_ver,hw_ver,md,cd):
    m_sf = struct.pack('B',sf)
    m_cmd = struct.pack('B',set_serial)
    m_fw = struct.pack('L', fw_ver)
    m_hw = struct.pack('L', hw_ver)
    m_ser = struct.pack('L',snum)
    m_mdate = struct.pack('L',md)
    m_cdate = struct.pack('L',cd)
    m_csum = struct.pack('B',0xBB)
    m_ef = struct.pack('B',ef)
    m_msg = m_cmd+m_fw+m_hw+m_ser+m_mdate+m_cdate+m_csum+m_ef
    m_len = struct.pack('B', len(m_msg))
    msg = m_sf+m_len+m_msg
    sport.write(msg)
    rsp = sport.read(100)
    get_ver_rsp = '<BBBLLLLLLLLLBB'
    print(rsp)
    flds = struct.unpack(get_ver_rsp,rsp)
#    print(flds)

# will need to pass fields back rather than
# just the array. 
def do_get_version(sport):
    sport.read(1000)
    cmd = struct.pack('bbbbb',sf,0x03,get_version,0x00,ef)
    sport.write(cmd)
    rsp = sport.read(100)
    print(rsp, len(rsp))
    get_ver_rsp = '<BBBLLLLLBB'
    get_ver_rsp = '<BBBLLLLLLLLLBB'
    
    flds = struct.unpack(get_ver_rsp,rsp)
    return flds

def do_get_adxl_info(sport):
    sport.read(1000)
    cmd = struct.pack('BBBBB', sf, 0x03, get_adxl_info, 0x00, ef)
    sport.write(cmd)
    rsp = sport.read(1000)
    print (rsp, len(rsp))
    adxl_rsp = '<BBBBBBBBBBBBBBBBBB'
    flds = struct.unpack(adxl_rsp, rsp)
    return flds[3:]

class configinfo:
    pass

def default_config():
    cfg = configinfo()
    cfg.c1ena = 1
    cfg.c2ena = 1
    cfg.peSensorEna = 0
    cfg.rchannel = 11
    cfg.txtime = 1
    cfg.prelen = 4
    cfg.txpow = 0
    cfg.config0 = 0x62
    cfg.config1 = 0x08
    cfg.hpf0 = 0x32
    cfg.hpf1 = 0x03
    cfg.ofc0 = 0x00
    cfg.ofc1 = 0x00
    cfg.ofc2 = 0x00
    cfg.fsc0 = 0x00
    cfg.fsc1 = 0x00
    cfg.fsc2 = 0x40
    return cfg

def do_set_config(sport,cfg):
    channel = struct.pack('BB',cfg.c1ena,cfg.c2ena,cfg.peSensorEna)
    radio = struct.pack('BBBB',cfg.rchannel,cfg.txtime,cfg.prelen,cfg.txpow)
    adsinfo = struct.pack('BBBBBBBBBB',cfg.config0,cfg.config1,cfg.hpf0,cfg.hpf1,
                          cfg.ofc0,cfg.ofc1,cfg.ofc2,cfg.fsc0,cfg.fsc1,cfg.fsc2)
    post_msg = struct.pack('BB',set_config,0x72)+adsinfo+radio+channel+struct.pack('BB',0x00,ef)
    pre_msg  = struct.pack('BB',sf,len(post_msg))
    msg = pre_msg+post_msg
    sport.write(msg)
    rsp = sport.read(100)
#    print("Resp: ", rsp)


def do_get_config(sport):
    cmd = struct.pack('BBBBB', sf,0x03,get_config,0x00,ef)
    sport.write(cmd)
    rsp = sport.read(100)
#    print(rsp,len(rsp))
    flds = struct.unpack(cfg_rsp, rsp)
    
    cfginfo = configinfo()
    cfginfo.cfggood = flds[3]
    cfginfo.ads_cfg0 = flds[4]
    cfginfo.ads_cfg1 = flds[5]
    cfginfo.ads_hpf0 = flds[6]
    cfginfo.ads_hpf1 = flds[7]
    cfginfo.ads_ofc0 = flds[8]
    cfginfo.ads_ofc1 = flds[9]
    cfginfo.ads_ofc2 = flds[10]
    cfginfo.ads_fsc0 = flds[11]
    cfginfo.ads_fsc1 = flds[12]
    cfginfo.ads_fsc2 = flds[13]
    cfginfo.radio_channel = flds[14]
    cfginfo.radio_sleep = flds[15]
    cfginfo.radio_pream = flds[16]
    cfginfo.radio_power = flds[17]
    cfginfo.chan1enable = flds[18]
    cfginfo.chan2enable = flds[19]
    cfginfo.peSensorEnable = flds[20]
                            
#    print(flds)
    return flds,cfginfo


def do_db_setup():
    c = db_conn.cursor()
    c.execute('''create table serialtb (serialnum int, bname text)''')
    c.execute('''create table manuf (cntrlid text, boardid serial, mfgdate text)''')
    db_conn.commit()

def init_sernum():
    c = db_conn.cursor()
    c.execute('insert into serialtb values(0,"rhino")')
    db_conn.commit()

def reset_serial(bname):
    c = db_conn.cursor()
    c.execute('update serialtb set serialnum=? where bname=?', (0,bname))
    db_conn.commit()
    
    
def get_next_serial():
    c = db_conn.cursor()
    c.execute('select * from serialtb ')
    sernum = c.fetchone()[0]
#    print ("Serial - ", sernum)
    nsernum = sernum + 1
    c.execute('update serialtb set serialnum=? where bname="rhino"', (nsernum,))
    db_conn.commit()
    return sernum

def add_board_to_db(cid,bid,mdate):
    c = db_conn.cursor()
    c.execute('insert into manuf values(?,?,?)',(cid,bid,mdate,))
    db_conn.commit()

# Setup board serial number.
# Get configuration information from the board.
# We expect the device to be already configured.
# FW/HW Versions are retreived from the device.
# Set the date. We just convert time.time (epoch)
# to a interger.
# get a new serial number.
# add information to the database.
# Only values that matter are the serial, manuf date and config date.
# all other values are ignored.

def setup_board_serial(sport):
    vers = do_get_version(sport)
    manuf_date = int(time.time())
    cfgd_date = int(time.time())
    snum = get_next_serial()
    cid = hex(vers[8])[2:].zfill(8)+hex(vers[9])[2:].zfill(8)+hex(vers[10])[2:].zfill(8)+hex(vers[11])[2:].zfill(8)
    add_board_to_db(cid,snum,time.ctime())
    do_set_version(sport,snum,0,0,manuf_date,cfgd_date)

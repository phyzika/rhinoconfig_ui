import serial
from serial.tools import list_ports
import threading
import queue
import struct
import socket
import signal
import sys
import time
import sqlite3

brate = 921600
get_version = 0x01
get_config = 0x02
set_config = 0x04
set_serial = 0x06
init_device = 0x07
read_init_device = 0x08
set_channel = 0x09
get_channel = 0x0A
set_sleep = 0x0B
get_sleep = 0x0C
wakeup_tx = 0x0E
set_wkup_code = 0x10
get_wkup_code = 0x11
start_logging = 0x12
stop_logging = 0x13
led_op = 0x14
get_radio_pv = 0x15
set_code_date = 0x16
get_uid = 0x17
tx_strobe = 0x18
set_filter = 0x19
get_filter = 0x20

sf = 0x02
ef = 0x03
def_sleep = 1
def_chnl = 11

wakeup_now = 0x62
wakeup_in_time = 0x73
wakeup_default = 0x84


db_conn = sqlite3.connect('rh_rx_cfg.db')

def do_db_setup():
    c = db_conn.cursor()
    c.execute('''create table serialtb (serialnum int, bname text)''')
    c.execute('''create table manuf (cntrlid text, boardid serial, mfgdate text)''')
    db_conn.commit()

def init_sernum():
    c = db_conn.cursor()
    c.execute('insert into serialtb values(0,"rhinorx")')
    db_conn.commit()

def set_next_serial(ser):
    c = db_conn.cursor()
    c.execute('update serialtb set serialnum=? where bname="rhinorx"', (ser,))
    db_conn.commit()
    
def reset_serial(bname):
    c = db_conn.cursor()
    c.execute('update serialtb set serialnum=? where bname=?', (0,bname))
    db_conn.commit()
    
    
def get_next_serial():
    c = db_conn.cursor()
    c.execute('select * from serialtb ')
    sernum = c.fetchone()[0]
    print ("Serial - ", sernum)
    nsernum = sernum + 1
    c.execute('update serialtb set serialnum=? where bname="rhinorx"', (nsernum,))
    db_conn.commit()
    return sernum

def add_board_to_db(cid,bid,mdate):
    c = db_conn.cursor()
    c.execute('insert into manuf values(?,?,?)',(cid,bid,mdate,))
    db_conn.commit()

def open_serial(ser):
    sport = serial.Serial(ser,3000000,timeout=0.1)
    sport.write("raw\r\n".encode("utf-8"))
    time.sleep(0.5)
    rsp = sport.read(100)
    print("Opened Rsp -- {0}".format(rsp))
    return sport
    
def setup_board_serial(ser,chnl):
    sport = serial.Serial(ser,3000000,timeout=0.1)
    do_init_device(sport)
    sernum = get_next_serial()
    mfgd = int(time.time())
    print("Mfgd - ", mfgd)
    do_set_config(sport,sernum,def_sleep,chnl,mfgd,0,wakeup_now,1)
    add_board_to_db(chnl,sernum,mfgd)
    doTestPrint("RHINO-"+str(sernum))
    return sport

def config_board(sport,chnl):
    snum = get_next_serial()
    mfgd = int(time.time())
    do_set_config(sport,snum,def_sleep,chnl,mfgd,0,wakeup_now,1)
    add_board_to_db(chnl,snum,mfgd)
    return snum

# initialize flash. 
def do_init_device(sport):
    sport.write("raw\r\n".encode("utf-8"))
    # sf, len, cmd, csum, ef
    csum = init_device + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,init_device, csum, ef)
    sport.write(m_msg)
    print("Wait for response ....")
    time.sleep(0.5)
    rsp = sport.read(100)
    time.sleep(0.5)
    print("Init Rsp -- {0}".format(rsp))

# set config.
# Format modified in 1.2 
# Sequence now is VALID|SERIAL|MFGDATE|CODEDATE|CHNL|SLP|WCODE
# L|L|L|L|B|B|B
def do_set_config(sport, srl, sleep,channel, mfgd, cddate, wkup,fil):
  
    vld = struct.pack('BBBB',ord('p'),ord('h'),ord('y'),ord('z'))
    srl = struct.pack('L',srl)
    slp = struct.pack('B',sleep)
    chnl = struct.pack('B',channel)
    mfg = struct.pack('L',mfgd)
    wcode = struct.pack('B',wkup)
    fenable = struct.pack('B', fil)
    cdl = struct.pack('L', 0x00000000)
    mlen = len(vld)+len(srl)+len(slp)+len(chnl)+len(mfg)+len(wcode)+len(fenable)+len(cdl)

    # EOF byte is not included in the packet lenght calculations. 
    mlen = mlen+2
    pream = struct.pack('BBBB',0x02,mlen,0x00,set_config)
    csum = struct.pack('B',0x00)
    postam = struct.pack('B',0x03)

    print("Message Length in msg - ", mlen)

    msg = pream +  vld + srl + mfg + cdl+chnl+slp+wcode+fenable+csum+postam
    print("Actual len: ", len(msg))
    print(msg)
   
    sport.write(msg)
    print("Wait for response - set config ....")
    time.sleep(0.5)
    rsp = sport.read(100)
    print("Config resp: ", rsp)

def do_get_config(sport):
    # sf, len,cmd,csum,ef
    csum = get_config + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,get_config,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    print(rsp,len(rsp))
    flds = struct.unpack('<BHBLLLLBBBBB',rsp)
    #print("Serial: {0}, Sleep: {1}, Channel: {2} filter: {3}".format(flds[4],flds[5],flds[6],flds[7]))
    return flds[4],flds[5],flds[8],flds[7],flds[9],flds[10]

def parseVersion(hwver,fwver):
        fmaj = hex(((fwver&0xFF00)>>8))
        fmin = hex(fwver&0x00FF)
        fver = fmaj[2:]+'.'+ fmin[2:]
        hmaj = hex((hwver&0xFF00)>>8)
        hmin = hex(hwver&0x00FF)
        hver = hmaj[2:]+'.'+hmin[2:]
        return hver,fver


def do_get_info(comport):
    hwver, fwver = do_get_version(comport)
    snum,mfgd, slp,chnl,wkupcode,local_filter = do_get_config(comport)
    print("Wkup Code Type: ",type(wkupcode))
    print(snum, hex(slp), chnl, wkupcode)
    print("Local filter enabled - ", local_filter)
    
    hver, fver = parseVersion(hwver, fwver)
    print(hver,fver)


def do_set_channel(sport,chnl):
    csum = set_channel + 0x03
    m_msg = struct.pack('BBBBBBB',sf,0x03,0x00,set_channel,chnl,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    print(rsp)
    
def do_set_filter(sport, filt):
    csum = set_filter + 0x03
    m_msg = struct.pack('BBBBBBB',sf,0x03,0x00,set_filter,filt,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    print(rsp)

def do_get_channel(sport):
    csum = get_channel + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,get_channel,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    flds = struct.unpack('BBBBBB',rsp)
    return flds[3]
    
    
def do_start_logging(sport):
    csum = start_logging + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,start_logging,csum,ef)
    sport.write(m_msg)
   
def do_stop_logging(sport):
    csum = stop_logging + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,stop_logging,csum,ef)
    sport.write(m_msg)

def do_set_sleep(sport,slp):
    csum = set_sleep + 0x03
    m_msg = struct.pack('BBBBBBB',sf,0x03,0x00,set_sleep,slp,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    return rsp

def do_get_sleep(sport):
    csum = get_sleep + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,get_sleep,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    flds = struct.unpack('BBBBBB',rsp)
    return flds[3]

def do_set_wkupcode(sport,wkup):
    csum = set_wkup_code + 0x03
    print("Wkup Type - ", type(wkup))
    m_msg = struct.pack('BBBBBBB',sf,0x03,0x00,set_wkup_code,wkup,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    return rsp

def do_get_wkupcode(sport):
    csum = get_wkup_code + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,get_wkup_code,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    flds = struct.unpack('BBBBBB',rsp)
    return flds[3]




def do_get_version(sport):
    sport.read(1000)
    csum = get_sleep + 0x03
    m_msg = struct.pack('BBBBBB',sf,0x02,0x00,get_version,csum,ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    if len(rsp) == 9:
        flds = struct.unpack('<BHBHHB', rsp)
        print(flds)
        return flds[3],flds[4]
    else:
        0,0
    
def do_get_radio_partver(sport, radio):
    sport.read(100)
    csum = get_radio_pv + 0x03
    m_msg = struct.pack('BBBBBBB', sf, 0x02, 0x00, get_radio_pv, radio, csum, ef)
    sport.write(m_msg)
    rsp = sport.read(100)
    if len(rsp) == 8:
        flds = struct.unpack('<BHBBBBB', rsp)
        return hex(flds[3])[2:], hex(flds[4])[2:], hex(flds[5])[2:]
    else:
        return 0,0,0
    
def do_tx_strobe(sport, radio, onoff): 
    sport.read(100)
    csum = tx_strobe + 0x03
    m_msg = struct.pack('BBBBBBBB', sf, 0x03,0x00, tx_strobe, radio, onoff, csum, ef)
    sport.write(m_msg)
    

def doTestPrint(snum):
    port = 9100
    hostip = "192.168.17.81"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((hostip,port))
    gwsernum = 'RHINO-83'
    print("Text to print: ", snum)
    if gwsernum == '':
        gwsernum = "lushSensor"
    pstr = "^XA^A0N,60,50^FO30,60^FD{0}^FS^XZ".format(snum)
    sock.send(pstr.encode("utf-8"))
    sock.close()
    

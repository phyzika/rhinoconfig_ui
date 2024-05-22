# rhino configurator.
# version 0.3
import serial
from serial.tools import list_ports
import threading
import queue
import struct
import socket
import signal
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget,QTabWidget
from PyQt5.QtWidgets import QTextEdit,QTableWidget, QTableWidgetItem,QLineEdit
from PyQt5.QtWidgets import *
from PyQt5  import QtCore, QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import time
from rh_serializer import *

cc1201txpower = ["12","11","10","9","8","7","6","5","4","3","2","1","0","-3","-6","-11"]
cc1201preamble = ["0","0.5","1","1.5","2","3","4","5","6","7","8","12","24","30"]


class ConfigApp(QMainWindow):
    def __init__(self,com):
        super(ConfigApp, self).__init__()
        self.title = "Rhino 1.2 Transmitter Configurator"
        #self.setMinimumSize(QSize(640,480))
        self.setWindowTitle(self.title)
        self.comport = serial.Serial(com,921600,timeout=1.0)
        self.comport.read(10000)
        self.setStyleSheet("background-color: white;")
        self.tapvalue = 4
        self.tapduration = 4
        self.latency = 0
        self.window =0
        self.thres_act = 0
        self.thres_inact = 0
        self.time_inact = 0
        self.act_inact_ctl = 0
        self.thresh_ff =0
        self.time_ff = 0
        self.range = 0
        self.tap_axes = 0
        self.chnloffset = 4

        # first get version.
        vflds = do_get_version(self.comport)
        serial_num = vflds[5]
        fw_ver = vflds[3]
        hw_ver = vflds[4]
        md = vflds[6]
        cd = vflds[7]
        uid_0 = hex(vflds[8])[2:].zfill(8)
        uid_1 = hex(vflds[9])[2:].zfill(8)
        uid_2 = hex(vflds[10])[2:].zfill(8)
        uid_3 = hex(vflds[11])[2:].zfill(8)        
        uid = uid_0+uid_1+uid_2+uid_3
        # Get config information.
        #
        cflds,cinfo = do_get_config(self.comport)
#        print (cflds)
#        print (cinfo)
        
        self.font = QFont()
        self.font.setPointSize(12)
        central = QWidget(self)
        self.setCentralWidget(central)
        vLayout = QVBoxLayout(self)
        central.setLayout(vLayout)
        title = QLabel("Rhino 1.2 Transmitor Configurator",self)
        title.setStyleSheet("font: 20px;font-style: italic")
        serLayout = QHBoxLayout(central)
        serLabel = QLabel("Serial Number: ", self)
        serNumLabel = QLabel(hex(serial_num)[2:].zfill(8), self)
        fwLabel = QLabel("FW Version: ", self)
#        fwLabel.setMargin(20)
        fwLabel.setFont(self.font)
        fwVersion = QLabel(hex(fw_ver)[2:].zfill(8),self)
        fwVersion.setFont(self.font)
        hwLabel = QLabel("HW Version: ",self)
        hwVersion = QLabel(hex(hw_ver)[2:].zfill(8),self)
        cntrlIdLabel = QLabel("Controller ID: ", self)
        cntrlId = QLabel(uid,self)
        hwLabel.setFont(self.font)
        hwVersion.setFont(self.font)
        serNumLabel.setFont(self.font)
        cntrlIdLabel.setFont(self.font)
        cntrlId.setFont(self.font)
        serLabel.setMargin(10)
        serLabel.setFont(self.font)
        serLayout.addWidget(serLabel)
        serLayout.addWidget(serNumLabel)
        serLayout.addWidget(fwLabel)
        serLayout.addWidget(fwVersion)
        serLayout.addWidget(hwLabel)
        serLayout.addWidget(hwVersion)
        serLayout.addWidget(cntrlIdLabel)
        serLayout.addWidget(cntrlId)
        serLayout.addStretch(1)

        savebutton = QPushButton("Save Radio and ADC Configuration", self)
        quitbutton = QPushButton("Quit", self)
        savebutton.setFont(self.font)
        quitbutton.setFont(self.font)
        savebutton.setStyleSheet("background-color: lightgreen")
        quitbutton.setStyleSheet("background-color: red")
        blayout = QHBoxLayout(self)
        blayout.addWidget(savebutton)
        #blayout.addWidget(quitbutton)
        savebutton.clicked.connect(self.do_save)
        quitbutton.clicked.connect(self.do_quit)
        
        
        chnlLayout = self.addChannelBlock()
        radLayout = self.addRadioBlock()
        cfg0Layout = self.adsConfig0Block()
        cfg1Layout = self.adsConfig1Block()
        hpfblock = self.hpfBlock()
        ofcblock = self.ofcBlock()
        fscblock = self.fscBlock()
        memsblk = self.make_mems_accel_cfg_block()
        vLayout.addWidget(title)
        vLayout.addLayout(serLayout)
        vLayout.addLayout(chnlLayout)
        vLayout.addLayout(radLayout)
        vLayout.addLayout(cfg0Layout)
        vLayout.addLayout(cfg1Layout)
        vLayout.addLayout(hpfblock)
        vLayout.addLayout(ofcblock)
        vLayout.addLayout(fscblock)
        
        vLayout.addLayout(blayout)
        vLayout.addLayout(memsblk)
        vLayout.addWidget(quitbutton)
       
        vLayout.addStretch(1)
        self.do_set_config_values(cinfo)
        self.fill_in_adxl_data()
    
    def fill_in_adxl_data(self):
        try:
            adxl_flds = do_get_adxl_info(self.comport)
            self.tap_threshold = adxl_flds[1];
            self.tap_duration = adxl_flds[2]
            self.tap_latency = adxl_flds[3]
            self.tap_window = adxl_flds[4]
            self.thresh_act = adxl_flds[5]
            self.thresh_inact = adxl_flds[6]
            self.time_inact = adxl_flds[7]
            self.act_inact_ctl = adxl_flds[8]
            self.thresh_ff = adxl_flds[9]
            self.thresh_time = adxl_flds[10]
            self.int_enable = adxl_flds[11]
            self.tap_axes = adxl_flds[12]
        
            # Setup up tap axes.
       
            if self.act_inact_ctl & 0x80 > 0x00:
                self.act_acdc_chk.setChecked(True)
            else:
                self.act_acdc_chk.setChecked(False)
            if self.act_inact_ctl & 0x40 > 0x00:
                self.act_x_ena_chk.setChecked(True)
            if self.act_inact_ctl & 0x20 > 0x00:
                self.act_y_ena_chk.setChecked(True)
            if self.act_inact_ctl & 0x10 > 0x00:
                self.act_z_ena_chk.setChecked(True)
            if self.act_inact_ctl & 0x08 > 0x00:
                self.inact_acdc_chk.setChecked(True)
            if self.act_inact_ctl & 0x04 > 0x00:
                self.inact_x_ena_chk.setChecked(True)
            if self.act_inact_ctl & 0x02 > 0x00:
                self.inact_y_ena_chk.setChecked(True)
            if self.act_inact_ctl & 0x01 > 0x00:
                self.inact_z_ena_chk.setChecked(True)
        
    
            self.activity_thres_ent.setText(str(self.thresh_act*(62.5/1000)) + ' G')
            self.inactivity_thres_ent.setText(str(self.thresh_inact*(62.5/1000)) + ' G')
            self.inact_time_ent.setText(str(self.time_inact)[:8] + ' secs')
            #self.freefall_thres_ent.setText(str(self.thresh_ff*(62.5/1000))[:8] + ' G')
            #self.freefall_time_ent.setText(str(self.thresh_time*(5/1000))[:8] + ' secs')
        except:
            print("No ADXL data available.")
        
    def make_mems_cfg_string(self):
        act_inact_ctl = 0x00
        if self.act_acdc_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x80
        if self.act_x_ena_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x40
        if self.act_y_ena_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x20
        if self.act_z_ena_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x10
        if self.inact_acdc_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x08
        if self.inact_x_ena_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x04
        if self.inact_y_ena_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x02
        if self.inact_z_ena_chk.isChecked():
            act_inact_ctl = act_inact_ctl | 0x01
        mems = struct.pack('<BBBBBBBBBBBBB', 0xE5, 0x00,0x00,0x00,0x00,self.thresh_act, 
                           self.thresh_inact, self.time_inact, act_inact_ctl,self.thresh_ff,
                           self.thresh_time, self.int_enable, self.tap_axes)
        return mems
    def make_tapg_slider(self):
        hbox = QHBoxLayout()
        #self.tapslider = QSlider(Qt.Horizontal)
        self.tapslider = QDial()
        self.tapslider.setMinimum(0)
        self.tapslider.setMaximum(256)
        self.tapslider.setValue(4)
        self.tapslider.valueChanged.connect(self.tapValueChange)
        #elf.tapgval = QLineEdit(self)
        #self.tapgval.setText(str(self.tapvalue)[:8]+ ' G')
        lbl = QLabel("Tap Threshold: ", self)
        lbl.setStyleSheet("font: 16px;font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.tapslider)
        #hbox.addWidget(self.tapgval)
        
        #return self.tapslider
        return hbox
    
    def tapDurationChange(self):
        self.tap_duration = self.tapdurslider.value()
        #self.tapdurentry.setText(str(self.tap_duration*0.000625)[:8] + ' secs')
    
    def make_tapdur_slider(self):
        hbox = QHBoxLayout()
        self.tapdurslider = QDial()
        self.tapdurslider.setMinimum(0)
        self.tapdurslider.setMaximum(256)
        self.tapdurslider.setValue(4)
        #self.tapdurentry = QLineEdit(self)
        #self.tapdurentry.setText(str(self.tapduration*0.000625)[:8] + ' secs')
        self.tapdurslider.valueChanged.connect(self.tapDurationChange)
        lbl = QLabel("Tap Duration: ", self)
        lbl.setStyleSheet("font: 16px;font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.tapdurslider)
        #hbox.addWidget(self.tapdurentry)
        return hbox
    
    def tapValueChange(self):
        self.tap_threshold = self.tapslider.value()
        self.tapgval.setText(str(self.tap_threshold*(62.5/1000))[:8]+' G')
       
    
    def make_tap_latency(self):
        hbox = QHBoxLayout()
        self.tap_latency_dial = QDial()
        self.tap_latency_dial.setMinimum(0)
        self.tap_latency_dial.setMaximum(255)
        self.tap_latency_dial.setValue(4)
        self.tap_latency_dial.valueChanged.connect(self.tap_latency_value_changed)
        #self.tap_latency_ent = QLineEdit(self)
        #self.tap_latency_ent.setText(str(self.tap_latency_dial.value()*(1.25/1000))[:8]+' secs')
        lbl = QLabel("Double Tap Latency")
        lbl.setStyleSheet("font: 16px;font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.tap_latency_dial)
        #hbox.addWidget(self.tap_latency_ent)
        return hbox
    
    def make_tap_window(self):
        hbox = QHBoxLayout()
        self.tap_window_dial = QDial()
        self.tap_window_dial.setMinimum(0)
        self.tap_window_dial.setMaximum(255)
        self.tap_window_dial.setValue(4)
        self.tap_window_dial.valueChanged.connect(self.tap_window_value_changed)
        self.tap_window_ent = QLineEdit(self)
        self.tap_window_ent.setText(str(self.tap_window_dial.value()*(1.25/1000))[:8] + ' secs')
        self.tap_window_dial.setToolTip("Time after which a new tap is detected, 0 disables the function.")
        lbl = QLabel("Tap Window")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.tap_window_dial)
        hbox.addWidget(self.tap_window_ent)
        return hbox
    
    def tap_window_value_changed(self):
        self.tap_window = self.tap_window_dial.value()
        self.tap_window_ent.setText(str(self.tap_window*(1.25/1000))[:8] + ' secs')
    
    def tap_latency_value_changed(self):
        self.tap_latency = self.tap_latency_dial.value()
        self.tap_latency_ent.setText(str (self.tap_latency * (1.25/1000))[:8] + ' secs')
    
    def make_thresh_activity_dial(self):
        hbox = QHBoxLayout()
        self.activity_thres_dial = QDial()
        self.activity_thres_dial.setMinimum(0)
        self.activity_thres_dial.setMaximum(255)
        self.activity_thres_dial.setValue(4)
        self.activity_thres_dial.valueChanged.connect(self.activity_thres_value_changed)
        self.activity_thres_ent = QLineEdit(self)
        self.activity_thres_ent.setReadOnly(True)
        self.activity_thres_ent.setText(str(self.activity_thres_dial.value()*(62.5/1000))[:8] + ' G')
        self.activity_thres_dial.setToolTip("G Threshold to detect activity - 0 could case undesirable behavior")
        lbl = QLabel("Activity Threshold")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.activity_thres_dial)
        hbox.addWidget(self.activity_thres_ent)
        return hbox
    
    def activity_thres_value_changed(self):
        self.thresh_act = self.activity_thres_dial.value()
        self.activity_thres_ent.setText(str(self.thresh_act*(62.5/1000)) + ' G')
        
    def make_thresh_inactivity_dial(self):
        hbox = QHBoxLayout()
        self.inactivity_thres_dial = QDial()
        self.inactivity_thres_dial.setMinimum(0)
        self.inactivity_thres_dial.setMaximum(255)
        self.inactivity_thres_dial.setValue(4)
        self.inactivity_thres_dial.valueChanged.connect(self.inactivity_thres_value_changed)
        self.inactivity_thres_ent = QLineEdit(self)
        self.inactivity_thres_ent.setReadOnly(True)
        self.inactivity_thres_ent.setText(str(self.inactivity_thres_dial.value()*(62.5/1000))[:8] + ' G')
        self.inactivity_thres_dial.setToolTip("G Threshold to detect activity - 0 could case undesirable behavior")
        lbl = QLabel("Inactivity Threshold")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.inactivity_thres_dial)
        hbox.addWidget(self.inactivity_thres_ent)
        return hbox        
    
    def inactivity_thres_value_changed(self):
        self.thresh_inact = self.inactivity_thres_dial.value()
        self.inactivity_thres_ent.setText(str(self.thresh_inact*(62.5/1000)) + ' G')
    
    def make_inactivity_time(self):
        hbox = QHBoxLayout()
        self.inact_time_dial = QDial()
        self.inact_time_dial.setMinimum(0)
        self.inact_time_dial.setMaximum(255)
        self.inact_time_dial.setValue(4)
        self.inact_time_dial.valueChanged.connect(self.inact_time_value_changed)
        self.inact_time_ent = QLineEdit(self)
        self.inact_time_ent.setReadOnly(True)
        self.inact_time_ent.setText(str(self.inact_time_dial.value()) + ' secs')
        lbl = QLabel("Inactivity Time")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.inact_time_dial)
        hbox.addWidget(self.inact_time_ent)
        hbox.addStretch(1)
        return hbox
    
    def act_inact_ctrl(self):
        vbox = QVBoxLayout()
        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()
        self.act_acdc_chk = QCheckBox("Activity AC/DC")
        self.act_x_ena_chk = QCheckBox("Activity X Enable")
        self.act_y_ena_chk = QCheckBox("Activity Y Enable")
        self.act_z_ena_chk = QCheckBox("Activity Z Enable")
        self.inact_acdc_chk = QCheckBox("Inactivity AC/DC")
        self.inact_x_ena_chk = QCheckBox("Inactivity X Enable")
        self.inact_y_ena_chk = QCheckBox("Inactivity Y Enable")
        self.inact_z_ena_chk = QCheckBox("Inactivity Z Enable")
        hbox1.addWidget(self.act_acdc_chk)
        hbox1.addWidget(self.act_x_ena_chk)
        hbox1.addWidget(self.act_y_ena_chk)
        hbox1.addWidget(self.act_z_ena_chk)
        #hbox1.addStretch(1)
        hbox2.addWidget(self.inact_acdc_chk)
        hbox2.addWidget(self.inact_x_ena_chk)
        hbox2.addWidget(self.inact_y_ena_chk)
        hbox2.addWidget(self.inact_z_ena_chk)
        #hbox2.addStretch(1)
        lbl = QLabel("Activity/Inactivity Axis Control")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        vbox.addWidget(lbl)
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        return vbox
    
    
    def inact_time_value_changed(self):
        self.time_inact = self.inact_time_dial.value()
        self.inact_time_ent.setText(str(self.time_inact)[:8] + ' secs')
    
    def freefall_thres_cntrl(self):
        hbox = QHBoxLayout()
        self.freefall_thres_dial = QDial()
        self.freefall_thres_dial.setMinimum(0)
        self.freefall_thres_dial.setMaximum(255)
        self.freefall_thres_dial.setValue(4)
        self.freefall_thres_dial.valueChanged.connect(self.freefall_thres_value_changed)
        self.freefall_thres_ent = QLineEdit(self)
        self.freefall_thres_ent.setText(str(self.freefall_thres_dial.value()*(62.5/1000))[:8] + ' G')
        self.freefall_thres_dial.setToolTip("Freefall threshold - value between 300mg and 600mg recommended")
        lbl = QLabel("Freefall Threshold")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.freefall_thres_dial)
        hbox.addWidget(self.freefall_thres_ent)
        return hbox
    
    def freefall_thres_value_changed(self):
        self.thresh_ff = self.freefall_thres_dial.value()
        self.freefall_thres_ent.setText(str(self.thresh_ff*(62.5/1000))[:8] + ' G')
    
    def make_tap_axes_cntrl(self):
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        self.double_tap_suppress_chk = QCheckBox("Suppress Double Tap")
        self.tap_x_enable = QCheckBox("Enable X Axis")
        self.tap_y_enable = QCheckBox("Enable Y Axis")
        self.tap_z_enable = QCheckBox("Enable Z Axis")
        lbl = QLabel("Tap Axes")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        vbox.addWidget(lbl)
        hbox.addWidget(self.double_tap_suppress_chk)
        hbox.addWidget(self.tap_x_enable)
        hbox.addWidget(self.tap_y_enable)
        hbox.addWidget(self.tap_z_enable)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        return vbox
    
    def freefall_time_cntrl(self):
        hbox = QHBoxLayout()
        self.freefall_time_dial = QDial()
        self.freefall_time_dial.setMinimum(0)
        self.freefall_time_dial.setMaximum(255)
        self.freefall_time_dial.setValue(4)
        self.freefall_time_dial.valueChanged.connect(self.freefall_time_value_changed)
        #self.freefall_time_ent = QLineEdit(self)
        #self.freefall_time_ent.setText(str(self.freefall_time_dial.value()*(5/1000))[:8] + ' secs5')
        self.freefall_time_dial.setToolTip("Freefall Time - minimum time all three axes need to be below the threshold to detect freefall")
        lbl = QLabel("Freefall Time")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        hbox.addWidget(lbl)
        hbox.addWidget(self.freefall_time_dial)
        #hbox.addWidget(self.freefall_time_ent)
        return hbox
    
    def freefall_time_value_changed(self):
        self.thresh_time = self.freefall_time_dial.value()
        self.freefall_time_ent.setText(str(self.thresh_time*(5/1000))[:8] + ' secs6')
    
    def make_interrupt_enable_cntrl(self):
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        self.single_tap_int_ena = QCheckBox("Single Tap")
        self.double_tap_int_ena = QCheckBox("Double Tap")
        self.activity_int_ena = QCheckBox("Activity")
        self.inactivity_int_ena = QCheckBox("Inactivity")
        self.freefall_int_ena = QCheckBox("Freefall")
        lbl = QLabel("Enable interrupts on")
        lbl.setStyleSheet("font: 16px; font-style: italic")
        hbox.addWidget(self.single_tap_int_ena)
        hbox.addWidget(self.double_tap_int_ena)
        hbox.addWidget(self.activity_int_ena)
        hbox.addWidget(self.inactivity_int_ena)
        hbox.addWidget(self.freefall_int_ena)
        hbox.addStretch(1)
        vbox.addWidget(lbl)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        return vbox
    
    def make_mems_accel_cfg_block(self):
        self.memsblock = QVBoxLayout(self)
        self.memsLabel = QLabel("MEMS Accelerometer", self)
        self.memsLabel.setStyleSheet("font: 20px;font-style: italic")
        #self.memsblock.addWidget(self.memsLabel)
        
        self.pause_sleep = QPushButton("Pause Sleep")
        self.pause_sleep.setStyleSheet("font: 20px; font-style: italic; background-color: yellow")
        self.pause_sleep.clicked.connect(self.do_pause_sleep)
        
        
        hblock = QHBoxLayout(self)
        hblock.addWidget(self.memsLabel)
        hblock.addWidget(self.pause_sleep)
        
        self.memsblock.addLayout(hblock)
        
        #tapThreshold = QLabel("Tap Configuration", self)
        #tapThreshold.setStyleSheet("font: 16px;font-style: italic")
        tapBlk = QVBoxLayout(self)
        #tapBlk.addLayout(self.make_tap_axes_cntrl())
        #tapBlk.addWidget(tapThreshold)
        taphblk = QHBoxLayout(self)
        #taphblk.addLayout(self.make_tapg_slider())
        #taphblk.addLayout(self.make_tapdur_slider())
        #tapBlk.addLayout(taphblk)
        #tapBlk.addStretch(1)
        tapltncblk = QHBoxLayout(self)
        #tapltncblk.addLayout(self.make_tap_latency())
        #tapltncblk.addLayout(self.make_tap_window())
        #tapltncblk.addStretch(1)
        act_inact_blk = QHBoxLayout(self)
        act_inact_blk.addLayout(self.make_thresh_activity_dial())
        act_inact_blk.addLayout(self.make_thresh_inactivity_dial())
        act_inact_blk.addLayout(self.make_inactivity_time())
        act_inact_blk.addStretch(1)
        
        
        freefall_blk = QHBoxLayout(self)
        #freefall_blk.addLayout(self.freefall_thres_cntrl())
        #freefall_blk.addLayout(self.freefall_time_cntrl())
        
        self.save_mems_button = QPushButton("Save MEMS Configuration")
        self.save_mems_button.setFont(self.font)
        self.save_mems_button.setStyleSheet("background-color: lightgreen")
        self.save_mems_button.clicked.connect(self.do_save_mems_cfg)
        
        #self.memsblock.addWidget(tapThreshold)
        #self.memsblock.addLayout(tapBlk)
        #self.memsblock.addLayout(tapltncblk)
        self.memsblock.addLayout(act_inact_blk)
        self.memsblock.addLayout(self.act_inact_ctrl())
        #self.memsblock.addLayout(freefall_blk)
        #self.memsblock.addLayout(self.make_interrupt_enable_cntrl())
        mems_button_box = QHBoxLayout()
        mems_button_box.addWidget(self.save_mems_button)
        #mems_button_box.addStretch(1)
        self.memsblock.addLayout(mems_button_box)
        self.memsblock.addStretch(1)
        #self.memsblock.addLayout(self.make_tap_latency())
        #self.memsblock.addLayout(self.make_tap_window())
        
        return self.memsblock
        
    def do_pause_sleep(self):
        self.comport.read(1000)
        cmd = struct.pack('bbbbb',sf,0x03,pause_sleep,0x00,ef)
        self.comport.write(cmd)
        
    def do_save_mems_cfg(self):
        print("Save MEMS configuration")
        memstr = self.make_mems_cfg_string()
        postmsg = struct.pack('B', set_adxl_info) + memstr + struct.pack('BB', 0x00, ef)
        msg = struct.pack('BB', sf, len(postmsg)) + postmsg
        print(msg)
        self.comport.write(msg)
        rsp = self.comport.read(100)
        
    def do_set_config_values(self,cfg):
        if cfg.chan1enable:
            self.channel1Enable.setChecked(True)
        if cfg.chan2enable:
            self.channel2Enable.setChecked(True)
        if cfg.peSensorEnable:
            self.peSensorEnable.setChecked(True)
        
#        print("Radio Channel: ", cfg.radio_channel)
#        print("Radio Sleep: ", cfg.radio_sleep)
        self.txTimeTxt.setText(str(cfg.radio_sleep))
        if cfg.radio_channel >= 4:
            self.chnloffset = 4
            self.usband.setChecked(True)
        else:
            self.chnloffset = 0
            self.euband.setChecked(True)
        self.chnlComboBox.setCurrentIndex(cfg.radio_channel - self.chnloffset)
        self.pream.setCurrentIndex(cfg.radio_pream)
        self.txPower.setCurrentIndex(cfg.radio_power)

        # Cfg0 settings:
        syncval = cfg.ads_cfg0 >> 7
        self.syncvals.setCurrentIndex(syncval)
        drvals = (cfg.ads_cfg0 >> 3)&0x07
        self.drvals.setCurrentIndex(drvals)
        phase = (cfg.ads_cfg0 >> 2)&0x01
        self.firvals.setCurrentIndex(phase)
        fltr = cfg.ads_cfg0 & 0x03
        self.fltrvals.setCurrentIndex(fltr)
        pga = cfg.ads_cfg1 & 0x07
        self.pgagainvals.setCurrentIndex(pga)
        pgaena = (cfg.ads_cfg1 >> 3) & 0x01
        self.pgachopvals.setCurrentIndex(pgaena)
        mux = (cfg.ads_cfg1 >> 4) & 0x07
        self.muxvals.setCurrentIndex(mux)
#        print (hex(cfg.ads_hpf0)[2:].zfill(2))
        self.hllTxt.setText(hex(cfg.ads_hpf0)[2:].zfill(2))
        self.hhlTxt.setText(hex(cfg.ads_hpf1)[2:].zfill(2))        
        self.ollTxt.setText(hex(cfg.ads_ofc0)[2:].zfill(2))
        self.omlTxt.setText(hex(cfg.ads_ofc1)[2:].zfill(2))
        self.ohlTxt.setText(hex(cfg.ads_ofc2)[2:].zfill(2))
        self.fllTxt.setText(hex(cfg.ads_fsc0)[2:].zfill(2))
        self.fmlTxt.setText(hex(cfg.ads_fsc1)[2:].zfill(2))
        self.fhlTxt.setText(hex(cfg.ads_fsc2)[2:].zfill(2))                        

        
    def do_save(self):
#        print ("Do Save.")
        # First get channel enable flags.
        c1ena = 0x00
        c2ena = 0x00
        peSensor = 0x00

        svCfgInfo = configinfo()
        
        if self.channel1Enable.isChecked():
            c1ena = 0x01
        if self.channel2Enable.isChecked():
            c2ena = 0x01
        if self.peSensorEnable.isChecked():
            peSensor = 0x01

        svCfgInfo.c1ena = c1ena
        svCfgInfo.c2ena = c2ena
        svCfgInfo.peSensorEna = peSensor
        
        channel = struct.pack('BBB',c1ena,c2ena,peSensor)
#        print ("Channel: ",channel)
        # Now check for radio
#        print ("Radio Channel - ", self.chnlComboBox.currentIndex())
        rchannel = self.chnloffset + self.chnlComboBox.currentIndex()
        txtime = int(self.txTimeTxt.text())
        if txtime > 0xFF:
            txtime = 255

        # Get the preamble length and transmit power.
        prelen = self.pream.currentIndex()
        txpow = self.txPower.currentIndex()

        svCfgInfo.rchannel = rchannel
        svCfgInfo.txtime = txtime
        svCfgInfo.prelen = prelen
        svCfgInfo.txpow = txpow
        
        radio = struct.pack('BBBB',rchannel,txtime,prelen,txpow)
        
#        print ("Radio: ", radio)
        # Now get the ads values.
        sync = self.syncvals.currentIndex()<<7
        data_rate = self.drvals.currentIndex()<<3
#        print ("Data Rate: ", hex(data_rate))
        
        phase = self.firvals.currentIndex() <<2
        fltr = self.fltrvals.currentIndex() << 0
        config0 = sync|0x40|data_rate|phase|fltr
#        print("Config0 - ", hex(config0))
        pga = self.pgagainvals.currentIndex()
        pgaenable = self.pgachopvals.currentIndex()<<3
        mux = self.muxvals.currentIndex()<<4
        config1 = pga|pgaenable|mux
        print("Config1 - ", hex(config1))
        hpf0 = self.validate_hex(self.hllTxt.text())
        hpf1 = self.validate_hex(self.hhlTxt.text())
        ofc0 = self.validate_hex(self.ollTxt.text())
        ofc1 = self.validate_hex(self.omlTxt.text())
        ofc2 = self.validate_hex(self.ohlTxt.text())
        fsc0 = self.validate_hex(self.fllTxt.text())
        fsc1 = self.validate_hex(self.fmlTxt.text())
        fsc2 = self.validate_hex(self.fhlTxt.text())
#        print(hex(hpf0),hex(hpf1),hex(ofc0),hex(ofc1),hex(ofc2),hex(fsc0),hex(fsc1),hex(fsc2))

        svCfgInfo.config0 = config0
        svCfgInfo.config1 = config1
        svCfgInfo.hpf0 = hpf0
        svCfgInfo.hpf1 = hpf1
        svCfgInfo.ofc0 = ofc0
        svCfgInfo.ofc1 = ofc1
        svCfgInfo.ofc2 = ofc2
        svCfgInfo.fsc0 = fsc0
        svCfgInfo.fsc1 = fsc1
        svCfgInfo.fsc2 = fsc2
        
        adsinfo = struct.pack('BBBBBBBBBB',config0,config1,hpf0,hpf1,
                              ofc0,ofc1,ofc2,fsc0,fsc1,fsc2)
        post_msg = struct.pack('BB',set_config,0x72)+adsinfo+radio+channel+struct.pack('BB',0x00,ef)
        pre_msg  = struct.pack('BB',sf,len(post_msg))
        msg = pre_msg+post_msg
        self.comport.write(msg)
        rsp = self.comport.read(100)
#        print("Resp: ", rsp)
        
        
    
    def do_quit(self):
#        print ("Do Quit")
        QCoreApplication.instance().quit()
        
    def addChannelBlock(self):
        cLayout = QHBoxLayout(self)
        chnlLabel = QLabel("Enable Channels", self)
        chnlLabel.setFont(self.font)
        chnlLabel.setMargin(10)
        cLayout.addWidget(chnlLabel)
        self.channel1Enable = QCheckBox("Channel 1")
        self.channel2Enable = QCheckBox("Channel 2")
        self.peSensorEnable = QCheckBox("Enable PE Sensor")
        
        self.euband = QRadioButton("EU863-870 Band")
        self.usband = QRadioButton("US902-928 Band")
        self.usband.setChecked(True)
        self.euband.setChecked(False)
        self.euband.toggled.connect(lambda: self.selectUSorEUBand(self.euband))
        self.usband.toggled.connect(lambda: self.selectUSorEUBand(self.usband))
        
        self.channel1Enable.setFont(self.font)
        self.channel2Enable.setFont(self.font)
        self.peSensorEnable.setFont(self.font)
        self.euband.setFont(self.font)
        self.usband.setFont(self.font)
        cLayout.addWidget(self.channel1Enable)
        cLayout.addWidget(self.channel2Enable)
        cLayout.addWidget(self.peSensorEnable)
        cLayout.addWidget(self.euband)
        cLayout.addWidget(self.usband)
        cLayout.addStretch(1)
#        print("Add Channel Block..")
        return cLayout
    
    def selectUSorEUBand(self, rbtn):        
        # remove items from channel list.
        # then recreate the list.
        while self.chnlComboBox.count():
            self.chnlComboBox.removeItem(0)
        
        if rbtn.text() == "EU863-870 Band":
            if rbtn.isChecked() == True:
                self.chnloffset = 0
                for i in range(4):
                    self.chnlComboBox.addItem(str(i))
            else:
                print (rbtn.text() + " is not selected")
        if rbtn.text() == "US902-928 Band":
            if rbtn.isChecked() == True:
                self.chnloffset = 4
                print (rbtn.text() + " is selected")
                for i in range(14):
                    self.chnlComboBox.addItem(str(i))
            else: 
                print (rbtn.text() + " is not selected")
            
    
    def addRadioBlock(self):
        rLayout = QHBoxLayout(self)
        radioLabel = QLabel("Radio Configuration", self)
        radioLabel.setFont(self.font)
        radioLabel.setMargin(10)
        chnlNumLabel = QLabel("Channel: ", self)
        chnlNumLabel.setFont(self.font)
        self.chnlComboBox = QComboBox(self)
        self.chnlComboBox.setFont(self.font)
        for i in range(14):
            self.chnlComboBox.addItem(str(i))
        txTime = QLabel("Default Transmit Time:")
        txTime.setFont(self.font)
        self.txTimeTxt = QLineEdit(self)
        self.txTimeTxt.setFont(self.font)
        self.txTimeTxt.setFixedWidth(50)
        txTimeMins = QLabel("mins")

        txPowerLabel = QLabel("Transmit Power", self)
        txPowerLabel.setFont(self.font)
        txPowerLabel.setMargin(10)
        self.txPower = QComboBox(self)
        self.txPower.addItems(cc1201txpower)
        txPowerLabel.setFont(self.font)
        self.txPower.setFont(self.font)
        
        preamLabel = QLabel("Preamble Bytes", self)
        preamLabel.setFont(self.font)
        preamLabel.setMargin(10)
        self.pream = QComboBox(self)
        self.pream.addItems(cc1201preamble)
        self.pream.setCurrentIndex(4)
        preamLabel.setFont(self.font)
        self.pream.setFont(self.font)

        
        
        txTimeMins.setFont(self.font)
        rLayout.addWidget(radioLabel)
        rLayout.addWidget(chnlNumLabel)
        rLayout.addWidget(self.chnlComboBox)
        rLayout.addWidget(txTime)
        rLayout.addWidget(self.txTimeTxt)
        rLayout.addWidget(txTimeMins)
        rLayout.addWidget(txPowerLabel)
        rLayout.addWidget(self.txPower)
        rLayout.addWidget(preamLabel)
        rLayout.addWidget(self.pream)
    
        rLayout.addStretch(1)
        return rLayout
            
    def adsConfig0Block(self):
        rLayout = QHBoxLayout(self)
        lbl = QLabel("ADS Config0",self)
        lbl.setFont(self.font)
        lbl.setMargin(10)
        sync = QLabel("Sync", self)
        sync.setFont(self.font)
        self.syncvals = QComboBox(self)
        self.syncvals.setFont(self.font)
        self.syncvals.addItem("Pulse")
        self.syncvals.addItem("Continuous Sync")
        drselect = QLabel("Data Rate", self)
        drselect.setFont(self.font)
        self.drvals = QComboBox(self)
        self.drvals.setFont(self.font)
        self.drvals.addItem("250 SPS")
        self.drvals.addItem("500 SPS")
        self.drvals.addItem("1000 SPS")
        self.drvals.addItem("2000 SPS")
        self.drvals.addItem("4000 SPS")
        firrsp = QLabel("FIR Phase Response", self)
        firrsp.setFont(self.font)
        self.firvals = QComboBox(self)
        self.firvals.setFont(self.font)
        self.firvals.addItem("Linear")
        self.firvals.addItem("Minimum")
        fltr = QLabel("Digital Filter Select", self)
        fltr.setFont(self.font)
        self.fltrvals = QComboBox(self)
        self.fltrvals.setFont(self.font)
        self.fltrvals.addItem("Filter Bypassed.")
        self.fltrvals.addItem("Sinc filter block only")
        self.fltrvals.addItem("Sinc + LPF")
        self.fltrvals.addItem("Sinc + LPF + HPF")
        rLayout.addWidget(lbl)
        rLayout.addWidget(sync)
        rLayout.addWidget(self.syncvals)
        rLayout.addWidget(drselect)
        rLayout.addWidget(self.drvals)
        rLayout.addWidget(firrsp)
        rLayout.addWidget(self.firvals)
        rLayout.addWidget(fltr)
        rLayout.addWidget(self.fltrvals)
        rLayout.addStretch(1)
        return rLayout

    def adsConfig1Block(self):
        rLayout = QHBoxLayout(self)
        lbl = QLabel("ADS Config1",self)
        lbl.setFont(self.font)
        lbl.setMargin(10)
        mux = QLabel("MUX Select")
        self.muxvals = QComboBox(self)
        self.muxvals.addItem("AINP1 and AINN1")
        self.muxvals.addItem("AINP2 and AINN2")
        self.muxvals.addItem("Internal short via 400Ohm")
        self.muxvals.addItem("AINP1 and AINN1 connected to AINP2 and AINN2")
        self.muxvals.addItem("External Short to AINN2")
        self.muxvals.setFont(self.font)
        mux.setFont(self.font)
        pgachop = QLabel("PGA Chopping Enable")
        pgachop.setFont(self.font)
        self.pgachopvals = QComboBox(self)
        self.pgachopvals.setFont(self.font)
        self.pgachopvals.addItem("Disable")
        self.pgachopvals.addItem("Enable")
        pgagain = QLabel("PGA Gain")
        pgagain.setFont(self.font)
        self.pgagainvals = QComboBox(self)
        self.pgagainvals.setFont(self.font)
        self.pgagainvals.addItem("1")
        self.pgagainvals.addItem("2")
        self.pgagainvals.addItem("4")
        self.pgagainvals.addItem("8")
        self.pgagainvals.addItem("16")
        self.pgagainvals.addItem("32")
        self.pgagainvals.addItem("64")
        rLayout.addWidget(lbl)
        rLayout.addWidget(mux)
        rLayout.addWidget(self.muxvals)
        rLayout.addWidget(pgachop)
        rLayout.addWidget(self.pgachopvals)
        rLayout.addWidget(pgagain)
        rLayout.addWidget(self.pgagainvals)
        rLayout.addStretch(1)
        return rLayout

    def hpfBlock(self):
        rLayout = QHBoxLayout(self)
        lbl = QLabel("High Pass Filter Corner Frequency")
        lbl.setFont(self.font)
        lbl.setMargin(10)
        hlbl = QLabel("High Byte:")
        hlbl.setFont(self.font)
        self.hhlTxt = QLineEdit(self)
        self.hhlTxt.setFont(self.font)
        self.hhlTxt.setFixedWidth(50)

        llbl = QLabel("Low Byte:")
        llbl.setFont(self.font)
        self.hllTxt = QLineEdit(self)
        self.hllTxt.setFont(self.font)
        self.hllTxt.setFixedWidth(50)

        rLayout.addWidget(lbl)
        rLayout.addWidget(llbl)
        rLayout.addWidget(self.hllTxt)
        rLayout.addWidget(hlbl)
        rLayout.addWidget(self.hhlTxt)

        rLayout.addStretch(1)
        return rLayout

    def ofcBlock(self):
        rLayout = QHBoxLayout(self)
        lbl = QLabel("Offset Calibration")
        lbl.setFont(self.font)
        lbl.setMargin(10)

        llbl = QLabel("Low Byte:")
        llbl.setFont(self.font)
        self.ollTxt = QLineEdit(self)
        self.ollTxt.setFont(self.font)
        self.ollTxt.setFixedWidth(50)

        mlbl = QLabel("Mid Byte:")
        mlbl.setFont(self.font)
        self.omlTxt = QLineEdit(self)
        self.omlTxt.setFont(self.font)
        self.omlTxt.setFixedWidth(50)

        hlbl = QLabel("High Byte:")
        hlbl.setFont(self.font)
        self.ohlTxt = QLineEdit(self)
        self.ohlTxt.setFont(self.font)
        self.ohlTxt.setFixedWidth(50)

        rLayout.addWidget(lbl)
        rLayout.addWidget(llbl)
        rLayout.addWidget(self.ollTxt)

        rLayout.addWidget(mlbl)
        rLayout.addWidget(self.omlTxt)

        rLayout.addWidget(hlbl)
        rLayout.addWidget(self.ohlTxt)
        rLayout.addStretch(1)
        return rLayout

    def fscBlock(self):
        rLayout = QHBoxLayout(self)
        lbl = QLabel("Full Scale Calibration")
        lbl.setFont(self.font)
        lbl.setMargin(10)

        llbl = QLabel("Low Byte:")
        llbl.setFont(self.font)
        self.fllTxt = QLineEdit(self)
        self.fllTxt.setFont(self.font)
        self.fllTxt.setFixedWidth(50)
        
        mlbl = QLabel("Mid Byte:")
        mlbl.setFont(self.font)
        self.fmlTxt = QLineEdit(self)
        self.fmlTxt.setFont(self.font)
        self.fmlTxt.setFixedWidth(50)

        hlbl = QLabel("High Byte:")
        hlbl.setFont(self.font)
        self.fhlTxt = QLineEdit(self)
        self.fhlTxt.setFont(self.font)
        self.fhlTxt.setFixedWidth(50)


        rLayout.addWidget(lbl)
        rLayout.addWidget(llbl)
        rLayout.addWidget(self.fllTxt)

        rLayout.addWidget(mlbl)
        rLayout.addWidget(self.fmlTxt)

        rLayout.addWidget(hlbl)
        rLayout.addWidget(self.fhlTxt)
        rLayout.addStretch(1)
        return rLayout

    def validate_hex(self, instr):
        if len(instr) != 2:
            return 0
        else:
            try:
                val = int(instr,16)
            except:
                val = 0
            return val
    
if __name__=="__main__":
    app = QApplication(sys.argv)
    if len(sys.argv) == 2:
        ex = ConfigApp(sys.argv[1])
        ex.show()
        sys.exit(app.exec_())
    else:
        print("rh_config <COMPORT>")
          

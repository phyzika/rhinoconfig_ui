# rhino configurator.
#
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
from rh_rx_config import *

class ConfigApp(QMainWindow):
    def __init__(self,com):
        super(ConfigApp,self).__init__()
        self.title = "Rhino Receiver Configuration"
        self.setMinimumSize(QSize(320,200))
        self.setWindowTitle(self.title)
        #self.comport = serial.Serial(com,921600,timeout=1.0)
        self.comport = serial.Serial(com, 3000000, timeout=1.0)
        self.setStyleSheet("background-color: white;")
        self.comport.read(1000)
        self.comport.write("raw\r\n".encode("utf-8"))
        self.chnloffset = 4;

        hwver, fwver = do_get_version(self.comport)
        snum,mfgd, slp,chnl,wkupcode,local_filter = do_get_config(self.comport)
        self.chnl = chnl
        print("Wkup Code Type: ",type(wkupcode))
        print(snum, hex(slp), chnl, wkupcode)
        print("Local filter enabled - ", local_filter)
        
        hver, fver =self.parseVersion(hwver, fwver)



        self.font = QFont()
        self.font.setPointSize(12)
        central = QWidget(self)
        self.setCentralWidget(central)
        vLayout = QVBoxLayout(self)
        central.setLayout(vLayout)
        title = QLabel("Rhino 1.2 Receiver Configurator",self)
        title.setStyleSheet("font: 20px;font-style: italic")
        vLayout.addWidget(title)
        verLayout = QHBoxLayout(self)
        hwlbl = QLabel("Hardware Version: " + hver + " Firmware Version: " + fver)
        hwlbl.setStyleSheet("font: 20px; font-style: italic")
        verLayout.addWidget(hwlbl)
        hLayout1 = QHBoxLayout(self)
        slbl = QLabel("Serial Number: " + str(snum), self)
        slbl.setStyleSheet("font: 18px;font-style: italic")
        hLayout1.addWidget(slbl)
        hLayout2 = QHBoxLayout(self)
        #slplbl = QLabel("Sleep Interval: ")
        #self.slptxt = QLineEdit(self)
        #self.slptxt.setFont(self.font)
        #self.slptxt.setFixedWidth(50)
        #slplbl.setStyleSheet("font: 18px;font-style: italic")
        #self.slptxt.setStyleSheet("font: 18px;font-style: italic")
        #slMins = QLabel("mins")
        #slMins.setStyleSheet("font: 18px;font-style: italic")
        vLayout3 = QVBoxLayout(self)
        #wkuplbl = QLabel("Wakeup Mode: ", self)
        #wkuplbl.setStyleSheet("font: 18px;font-style: italic")
        vhLayout4 = QHBoxLayout(self)

        

        self.wkupTrans = QRadioButton("Default - Transmitter Default")
        self.wkupImmed = QRadioButton("Wakeup Immediate - Transmit Continous")
        self.wkupRxSleep = QRadioButton("Wakeup After RX Sleep")

        if wkupcode == wakeup_default:
            self.wkupcode = wakeup_default
            self.wkupTrans.setChecked(True)
        elif wkupcode == wakeup_in_time:
            self.wkupcode = wakeup_in_time
            self.wkupRxSleep.setChecked(True)
        elif wkupcode == wakeup_now:
            self.wkupcode = wakeup_now
            self.wkupImmed.setChecked(True)
        else:
            self.wkupcode = wakeup_default
            self.wkupTrans.setChecked(True)
        
        self.wkupImmed.setStyleSheet("font: 18px;font-style: italic")
        self.wkupTrans.setStyleSheet("font: 18px;font-style: italic")
        self.wkupRxSleep.setStyleSheet("font: 18px;font-style: italic")
#        self.wkupTrans.toggled.connect(self.wkup_btnstate(self.wkupTrans))
#        self.wkupImmed.toggled.connect(self.wkup_btnstate(self.wkupImmed))
#        self.wkupRxSleep.toggled.connect(wkup_btnstate(self.wkupRxSleep))
       # vhLayout4.addWidget(self.wkupTrans)
       # vhLayout4.addWidget(self.wkupImmed)
        vhLayout4.addWidget(self.wkupRxSleep)
        #vLayout3.addWidget(wkuplbl)
        vLayout3.addLayout(vhLayout4)
        fltr_label = QLabel("Filter Mode:")
        fltr_label.setStyleSheet("font: 18px;font-style: italic")
        self.fltr_enable = QCheckBox("Filter on device")
        self.fltr_enable.setStyleSheet("font: 18px;font-style: italic")        
        hlayout5 = QHBoxLayout(self)
        hlayout5.addWidget(fltr_label)
        hlayout5.addWidget(self.fltr_enable)
        hlayout5.addStretch()
        if local_filter > 0:
            self.fltr_enable.setChecked(True)
        else:
            self.fltr_enable.setChecked(False)
        
        
        #hLayout2.addWidget(slplbl)
        # hLayout2.addWidget(self.slptxt)
        #hLayout2.addWidget(slMins)
        #hLayout2.addStretch(1)

        hLayout6 = QHBoxLayout()
        self.euband = QRadioButton("EU863-870 Band")
        self.usband =  QRadioButton("US902-928 Band")
        self.euband.toggled.connect(lambda: self.selectUSorEUBand(self.euband))
        self.usband.toggled.connect(lambda: self.selectUSorEUBand(self.usband))
        self.euband.setFont(self.font)
        self.usband.setFont(self.font)
        hLayout6.addWidget(self.euband)
        hLayout6.addWidget(self.usband)
        hLayout6.addStretch(1)


        hLayout3 = QHBoxLayout(self)
        chnllbl = QLabel("Channel Number: ")
        self.chnlbox = QComboBox(self)
        self.chnlbox.setFont(self.font)
        self.chnlbox.setFixedWidth(50)
        for i in range(14):
            self.chnlbox.addItem(str(i))
        chnllbl.setStyleSheet("font: 18px;font-style: italic")
        self.chnlbox.setStyleSheet("font: 18px;font-style: italic")        
        
        
        hLayout3.addWidget(chnllbl)
        hLayout3.addWidget(self.chnlbox)
        hLayout3.addStretch(1)
        
        if self.chnl >= 4:
            self.chnloffset = 4
            self.usband.setChecked(True)
        else:
            self.chnloffset = 0
            self.euband.setChecked(True)
        
        self.chnlbox.setCurrentIndex(chnl-self.chnloffset)
        #self.slptxt.setText(str(slp))

        savebutton = QPushButton("Save", self)
        quitbutton = QPushButton("Quit", self)
        savebutton.setFont(self.font)
        quitbutton.setFont(self.font)
        savebutton.setStyleSheet("background-color: lightgreen")
        quitbutton.setStyleSheet("background-color: red")

        hLayout4 = QHBoxLayout(self)
        hLayout4.addWidget(savebutton)
        hLayout4.addWidget(quitbutton)

        savebutton.clicked.connect(self.do_save)
        quitbutton.clicked.connect(self.do_quit)
        
        vLayout.addLayout(verLayout)
        vLayout.addLayout(hLayout1)
        #vLayout.addLayout(hLayout2)
        vLayout.addLayout(hLayout6)
        vLayout.addLayout(hLayout3)
        vLayout.addLayout(hlayout5)
        #vLayout.addLayout(vLayout3)
        vLayout.addLayout(hLayout4)
       
        vLayout.addStretch(1)
        
    def selectUSorEUBand(self, rbtn):
        
        # remove items from channel list.
        # then recreate the list.
        while self.chnlbox.count():
            self.chnlbox.removeItem(0)
        
        if rbtn.text() == "EU863-870 Band":
            if rbtn.isChecked() == True:
                self.chnloffset = 0
                for i in range(4):
                    self.chnlbox.addItem(str(i))
            
        if rbtn.text() == "US902-928 Band":
            if rbtn.isChecked() == True:
                self.chnloffset = 4
                for i in range(14):
                    self.chnlbox.addItem(str(i))
           
        self.chnlbox.setCurrentIndex(self.chnl-self.chnloffset)
        
        if rbtn.text() == "EU863-870 Band":
            if self.chnl-self.chnloffset >= 4:
                self.chnlbox.setCurrentIndex(0)

        if rbtn.text() == "US902-928 Band":
            if rbtn.isChecked() == True:
                if (self.chnl-self.chnloffset) < 0:
                    self.chnlbox.setCurrentIndex(0)

    def parseVersion(self, hwver,fwver):
        fmaj = hex(((fwver&0xFF00)>>8))
        fmin = hex(fwver&0x00FF)
        fver = fmaj[2:]+'.'+ fmin[2:]
        hmaj = hex((hwver&0xFF00)>>8)
        hmin = hex(hwver&0x00FF)
        hver = hmaj[2:]+'.'+hmin[2:]
        return hver,fver

    def wkup_btnstate(self):
        self.wkupcode = wakeup_default
        if self.wkupTrans.isChecked():
            self.wkupcode = wakeup_default
        if self.wkupImmed.isChecked():
            self.wkupcode = wakeup_now
        if self.wkupRxSleep.isChecked():
            self.wkupcode = wakeup_in_time
        return self.wkupcode
        
    def do_save(self):
        print("Do Save")
        #print("sleep: ", int(self.slptxt.text()))
        print("channel: ", self.chnlbox.currentIndex())
        #self.wkup_btnstate()
        #do_set_sleep(self.comport, int(self.slptxt.text()))
        do_set_channel(self.comport, self.chnlbox.currentIndex() + self.chnloffset)
        #do_set_wkupcode(self.comport,self.wkupcode)
        if self.fltr_enable.isChecked(): 
            do_set_filter(self.comport, 1)
        else:
            do_set_filter(self.comport, 0)

    def do_quit(self):
        QCoreApplication.instance().quit()
        
if __name__=="__main__":
    app = QApplication(sys.argv)
    ex = ConfigApp(sys.argv[1])
    ex.show()
    sys.exit(app.exec_())

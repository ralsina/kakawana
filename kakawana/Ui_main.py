# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created: Mon Feb 22 09:37:26 2010
#      by: PyQt4 UI code generator 4.7
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QtGui.QSplitter(self.centralwidget)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.feeds = QtGui.QListWidget(self.splitter)
        self.feeds.setObjectName("feeds")
        self.html = QtWebKit.QWebView(self.splitter)
        self.html.setUrl(QtCore.QUrl("about:blank"))
        self.html.setObjectName("html")
        self.verticalLayout.addWidget(self.splitter)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 24))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.toolBar = QtGui.QToolBar(MainWindow)
        self.toolBar.setObjectName("toolBar")
        MainWindow.addToolBar(QtCore.Qt.TopToolBarArea, self.toolBar)
        self.actionNext = QtGui.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/next.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionNext.setIcon(icon)
        self.actionNext.setObjectName("actionNext")
        self.actionPrevious = QtGui.QAction(MainWindow)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/previous.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionPrevious.setIcon(icon1)
        self.actionPrevious.setObjectName("actionPrevious")
        self.actionNew_Feed = QtGui.QAction(MainWindow)
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/icons/filenew.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionNew_Feed.setIcon(icon2)
        self.actionNew_Feed.setObjectName("actionNew_Feed")
        self.actionDelete_Feed = QtGui.QAction(MainWindow)
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/icons/close.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionDelete_Feed.setIcon(icon3)
        self.actionDelete_Feed.setObjectName("actionDelete_Feed")
        self.toolBar.addAction(self.actionNew_Feed)
        self.toolBar.addAction(self.actionDelete_Feed)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionPrevious)
        self.toolBar.addAction(self.actionNext)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.toolBar.setWindowTitle(QtGui.QApplication.translate("MainWindow", "toolBar", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNext.setText(QtGui.QApplication.translate("MainWindow", "Next", None, QtGui.QApplication.UnicodeUTF8))
        self.actionPrevious.setText(QtGui.QApplication.translate("MainWindow", "Previous", None, QtGui.QApplication.UnicodeUTF8))
        self.actionNew_Feed.setText(QtGui.QApplication.translate("MainWindow", "New Feed", None, QtGui.QApplication.UnicodeUTF8))
        self.actionDelete_Feed.setText(QtGui.QApplication.translate("MainWindow", "Delete Feed", None, QtGui.QApplication.UnicodeUTF8))

from PyQt4 import QtWebKit
import icons_rc

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    MainWindow = QtGui.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())


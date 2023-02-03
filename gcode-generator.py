#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os

try:
	import gettext
	try:
		gettext.translation('base', localedir='locales').install()

	except Exception as e:
		print(str(e))
		gettext.translation('base', localedir='locales', languages=['en']).install()

except Exception as e:
	print(str(e))
	_ = lambda s:s


VERSION = "1.18"

try:
	parentProcess = os.popen("ps -o cmd= %d" % os.getppid()).read().strip()
except:
	parentProcess = "UNKNOWN"

try:
	# sudo apt-get install python3-pyqt5
	from PyQt5.QtGui import *
	from PyQt5.QtCore import *
	from PyQt5.QtWidgets import *
except:
	# sudo apt-get install python-qtpy python3-qtpy
	from PyQt4.QtGui import *
	from PyQt4.QtCore import *

class MyQDoubleSpinBox(QDoubleSpinBox):
	def __init__(self, defaultValue=0, minimum=-9999, maximum=9999, layout=None, layoutArgs=None):
		QDoubleSpinBox.__init__(self)
		self.setMinimum(minimum)
		self.setMaximum(maximum)
		self.setValue(defaultValue)
		if layout != None:
			layout.addWidget(self, *layoutArgs)

class MyQButtonGroup(QButtonGroup):
	def __init__(self, radioButtonsText=[], radioButtonsValues=[], checkedId=0, layout=None, layoutArgs=[]):
		QButtonGroup.__init__(self)
		layoutRadio = QHBoxLayout()
		radioButtons = []
		for i, t in enumerate(radioButtonsText):
			b = QRadioButton(t)
			self.addButton(b)
			self.setId(b, i)
			layoutRadio.addWidget(b)
			if i == checkedId:
				b.setChecked(True)
			try:
				b.value = radioButtonsValues[i]
			except:
				b.value = None
			radioButtons.append(b)

		layoutRadio.addStretch()
		layout.addLayout(layoutRadio, *layoutArgs)

	def value(self):
		return self.checkedButton().value

def nextpass(v, v_start, v_end, v_step):
	finished = False
	if v_end < v_start:
		v-=v_step
		if v <= v_end:
			v = v_end; finished = True
	else:
		v+=v_step
		if v >= v_end:
			v = v_end; finished = True
	return v, finished

class OperationHelicoidal(QWidget):
	tabTitle = _("Helicoidal")
	def __init__(self):
		QWidget.__init__(self)
		l = QGridLayout(self)

		# center position
		l.addWidget(QLabel(_("X/Y center position")))
		self.centerXpos = MyQDoubleSpinBox(layout=l, layoutArgs=(0, 1))
		self.centerYpos = MyQDoubleSpinBox(layout=l, layoutArgs=(0, 2))

		# diameter
		l.addWidget(QLabel(_("Circular movement diameter")), 1, 0)
		self.diameter = MyQDoubleSpinBox(50.0, minimum=0, layout=l, layoutArgs=(1, 1, 1, 2))

		# milling direction
		l.addWidget(QLabel(_("Milling direction")), 2, 0)
		self.millingDirectionBG = MyQButtonGroup((_("G02 (CW)"), _("G03 (CCW)")), ("G02", "G03"), 1, layout=l, layoutArgs=(2, 1, 1, 2))

		# finishing plane
		l.addWidget(QLabel(_("Do a flat turn at the bottom")), 3, 0)
		self.finishing_planeBG = MyQButtonGroup((_("Yes"), _("No")), (True, False), 0, layout=l, layoutArgs=(3, 1, 1, 2))

		# rotative pullout
		l.addWidget(QLabel(_("Rotative pull-out")), 4, 0)
		self.rotative_pulloutBG = MyQButtonGroup((_("Yes"), _("No")), (True, False), 1, layout=l, layoutArgs=(4, 1, 1, 2))

		l.setRowStretch(100, 10)

	def generate(self, fd, **kwargs):
		def kwget(kw, defaultValue=0):
			try: return kwargs[kw]
			except: return defaultValue

		center_x = self.centerXpos.value() + kwget('offset_x')
		center_y = self.centerYpos.value() + kwget('offset_y')
		radius   = self.diameter.value() / 2.0
		plunge_rate = kwget('plunge_rate', 30)
		feed_rate = kwget('feed_rate', 300)
		start_z = kwget('start_z', 0)
		end_z = kwget('end_z', -10)
		cutting_depth = kwget('cutting_depth', 1)

		fd.write("G00 X%g Y%g (rapid XY move to start position)\n"     % (center_x+radius, center_y))
		fd.write("G01 F%g Z%g (plunge slowly at surface)\n"             % (plunge_rate, start_z))

		code = self.millingDirectionBG.value()

		z = start_z
		while z > end_z+0.01:
			fd.write("%s F%g X%g Y%g R%g Z%g\n"                          % (code, feed_rate, center_x-radius, center_y, radius, z-cutting_depth/2))
			fd.write("%s F%g X%g Y%g R%g Z%g\n"                          % (code, feed_rate, center_x+radius, center_y, radius, z-cutting_depth))
			z-=cutting_depth
			if z-cutting_depth < end_z:
				cutting_depth = z-end_z

		if self.finishing_planeBG.value():
			fd.write("%s F%g X%g Y%g R%g (finishing pass, arc 1/2)\n"          % (code, feed_rate, center_x-radius, center_y, radius))
			fd.write("%s F%g X%g Y%g R%g (finishing pass, arc 2/2)\n"          % (code, feed_rate, center_x+radius, center_y, radius))

		if self.rotative_pulloutBG.value():
			fd.write("%s F%g X%g Y%g R%g Z%g (rotative pull-out 1/2)\n" % (code, feed_rate, center_x-radius, center_y, radius, (start_z+end_z)/2))
			fd.write("%s F%g X%g Y%g R%g Z%g (rotative pull-out 2/2)\n" % (code, feed_rate, center_x+radius, center_y, radius, start_z))

		fd.write("G00 Z%g (move 3mm from the surface)\n" % (start_z+3))

class OperationAlternateMilling(QWidget):
	tabTitle = _("Zig-zag")
	def __init__(self):
		QWidget.__init__(self)
		l = QGridLayout(self)

		# start position
		l.addWidget(QLabel(_("Start corner X/Y position")))
		self.startXpos = MyQDoubleSpinBox(layout=l, layoutArgs=(0, 1))
		self.startYpos = MyQDoubleSpinBox(layout=l, layoutArgs=(0, 2))

		# end position
		l.addWidget(QLabel(_("Opposite corner X/Y position")))
		self.endXpos = MyQDoubleSpinBox(layout=l, layoutArgs=(1, 1))
		self.endYpos = MyQDoubleSpinBox(layout=l, layoutArgs=(1, 2))

		# milling axis
		l.addWidget(QLabel(_("Mill along axis")), 2, 0)
		self.millingAlongAxisBG = MyQButtonGroup((_("X"), _("Y")), ('x', 'y'), 0, layout=l, layoutArgs=(2, 1, 1, 2))

		# milling band wideness
		l.addWidget(QLabel(_("Passes horizontal wideness")))
		self.horizontalPassWidth = MyQDoubleSpinBox(5, layout=l, layoutArgs=(3, 1, 1, 2))

		l.setRowStretch(100, 10)

	def generate(self, fd, **kwargs):
		def kwget(kw, defaultValue=0):
			try: return kwargs[kw]
			except: return defaultValue

		start_x = self.startXpos.value() + kwget('offset_x')
		start_y = self.startYpos.value() + kwget('offset_y')
		end_x   = self.endXpos.value()   + kwget('offset_x')
		end_y   = self.endYpos.value()   + kwget('offset_y')
		width   = self.horizontalPassWidth.value()
		milling_axis = self.millingAlongAxisBG.value()
		plunge_rate = kwget('plunge_rate', 30)
		feed_rate = kwget('feed_rate', 300)
		start_z = kwget('start_z', 0)
		end_z = kwget('end_z', -10)
		cutting_depth = kwget('cutting_depth', 1)

		# Z loop
		z = start_z; z_finished = False; evenpass = False
		while (not z_finished):
			# change Z
			z, z_finished = nextpass(z, start_z, end_z, cutting_depth)
			if not evenpass:
				fd.write('G00 X%g Y%g (rapid XY move to start position)\n' % (start_x, start_y))
			fd.write('G01 F%g Z%g (descend to next pass)\n' % (plunge_rate, z))

			if milling_axis == 'x':
				y = start_y; y_finished = False;
				fd.write('G01 F%g X%g Y%g\n' % (feed_rate, start_x if evenpass else end_x, y))
				if start_y == end_y: # special case
					evenpass = not evenpass
					continue

				while(not y_finished): # Y loop
					y, y_finished = nextpass(y, start_y, end_y, width)
					fd.write('G01 Y%g\n' % y)
					fd.write('G01 X%g\n' % (end_x if evenpass else start_x))
					evenpass = not evenpass

			if milling_axis == 'y':
				x = start_x; x_finished = False;
				fd.write('G01 F%g X%g Y%g\n' % (feed_rate, x, start_y if evenpass else end_y))
				if start_x == end_x: # special case
					evenpass = not evenpass
					continue

				while(not x_finished): # X loop
					x, x_finished = nextpass(x, start_x, end_x, width)
					fd.write('G01 X%g\n' % x)
					fd.write('G01 Y%g\n' % (end_y if evenpass else start_y))
					evenpass = not evenpass

			evenpass = False
			fd.write('G00 Z%g (1mm distance from surface on Z axis)\n' % (z + 1))

class OperationPath(QWidget):
	tabTitle = _("Path")
	YES = 1; NO = 0; BACK_AND_FORTH = 2
	def __init__(self):
		QWidget.__init__(self)
		l = QGridLayout(self)
		l.addWidget(QLabel(_("X Y coordinates")+"\n"+_("(separated by semicolons or newlines)")), 0, 0, 1, 2)
		self.editor = QTextEdit()
		self.editor.setPlainText("0.0 0.0\n0.0 10.0\n10.0 10.0\n10.0 0")
		self.editor.sizeHint = lambda: QSize(-1, -1)
		self.editor.minimumSizeHint = lambda: QSize(10, 10)
		l.addWidget(self.editor, 1, 0, 1, 2)

		# mill to start position to close path or not
		l.addWidget(QLabel(_("Close tool path")), 2, 0)
		self.closePathBG = MyQButtonGroup((_("Yes"), _("No"), _("Back and forth")), (self.YES, self.NO, self.BACK_AND_FORTH), 0, layout=l, layoutArgs=(2, 1, 1, 1))

	def generate(self, fd, **kwargs):
		def kwget(kw, defaultValue=0):
			try: return kwargs[kw]
			except: return defaultValue

		closePath = self.closePathBG.value()
		plunge_rate = kwget('plunge_rate', 30)
		feed_rate = kwget('feed_rate', 300)
		start_z = kwget('start_z', 0)
		end_z = kwget('end_z', -10)
		cutting_depth = kwget('cutting_depth', 1)

		coordinatesList = []
		for coordinatesStr in self.editor.toPlainText().replace(";", "\n").split("\n"):
			if len(coordinatesStr) < 1:
				continue
			coords = coordinatesStr.split()
			if len(coords) != 2:
				raise Exception(_("Incorrect amount of coordinates: ")+coordinatesStr)
			x = float(coords[0]) + kwget('offset_x')
			y = float(coords[1]) + kwget('offset_y')
			coordinatesList.append((x, y))

		# Z loop
		z = start_z; z_finished = False; first=True
		while (not z_finished):
			# change Z
			z, z_finished = nextpass(z, start_z, end_z, cutting_depth)

			if first or closePath == self.NO:
				fd.write('G00 X%g Y%g (rapid move to start position)\n' % (coordinatesList[0][0], coordinatesList[0][1]))
				if not first:
					fd.write('G00 Z%g (0.5mm distance from LAST surface on Z axis)\n' % (lastZ + 0.5))
				first = False

			fd.write('G01 F%g Z%g (descend to next pass)\n' % (plunge_rate, z))

			for x, y in coordinatesList[1:]:
				fd.write("G01 F%g X%g Y%g\n" % (feed_rate, x, y))

			if closePath == self.YES:
				fd.write("G01 X%g Y%g (closing shape)\n" % (coordinatesList[0][0], coordinatesList[0][1]))
			elif closePath == self.NO:
				fd.write('G00 Z%g (2mm distance from surface on Z axis)\n' % (start_z + 2))
				lastZ = z
			elif closePath == self.BACK_AND_FORTH: # TODO: test this!
				z, z_finished = nextpass(z, start_z, end_z, cutting_depth)
				if not z_finished:
					fd.write('G01 F%g Z%g (descend for backward pass)\n' % (plunge_rate, z))
					for x, y in reversed(coordinatesList[:-1]):
						fd.write("G01 F%g X%g Y%g\n" % (feed_rate, x, y))
			else:
				raise Exception(_("Missing condition"))

class OperationDrilling(QWidget):
	tabTitle = _("Drilling")
	def __init__(self):
		QWidget.__init__(self)
		l = QGridLayout(self)
		l.addWidget(QLabel(_("X Y or X Y Z coordinates")+"\n"+_("(separated by semicolons or newlines)")), 0, 0, 1, 2)
		self.editor = QTextEdit()
		self.editor.setPlainText("0.0 0.0; 0.0 10.0; 0 20.0\n10.0 0.0; 10.0 10.0; 10.0 20.0\n20.0 0.0; 20.0 10; 20.0 20.0")
		self.editor.sizeHint = lambda: QSize(-1, -1)
		self.editor.minimumSizeHint = lambda: QSize(10, 10)
		l.addWidget(self.editor, 1, 0, 1, 2)

		l.addWidget(QLabel(_("Setback height from surface")), 3, 0, 1, 1)
		self.retractHeight = MyQDoubleSpinBox(0.5, layout=l, layoutArgs=(3, 1, 1, 1))

	def generate(self, fd, **kwargs):
		# https://gcodetutor.com/fanuc-training-course/g73-g83-drilling-cycle.html
		def kwget(kw, defaultValue=0):
			try: return kwargs[kw]
			except: return defaultValue

		plunge_rate = kwget('plunge_rate', 30)
		start_z = kwget('start_z', 0)
		end_z = kwget('end_z', -1)
		cutting_depth = kwget('cutting_depth', 1)

		coordinatesStrList = self.editor.toPlainText()
		coordinatesStrList = coordinatesStrList.replace(";", "\n")
		for coordinatesStr in coordinatesStrList.split("\n"):
			if len(coordinatesStr) < 1:
				continue
			coords = coordinatesStr.split()
			if len(coords) > 3 or len(coords) < 2:
				raise Exception(_("Incorrect amount of coordinates: ")+coordinatesStr)
			x = float(coords[0]) + kwget('offset_x')
			y = float(coords[1]) + kwget('offset_y')
			if len(coords) > 2:
				z = max(float(coords[2]), end_z)
			else:
				z = end_z
			r = start_z + self.retractHeight.value()
			fd.write("G00 X%g Y%g\n" % (x, y))
			fd.write("G00 Z%g\n" % (start_z+0.5))
			fd.write("G83 Z%g R%g F%g Q%g\n" % (z, r, plunge_rate, cutting_depth))
			fd.write("G00 Z%g\n" % (start_z+3))

class About(QWidget):
	tabTitle = _("About")
	generate = None
	def __init__(self):
		QWidget.__init__(self)
		hl = QHBoxLayout(self)

		def lnk(url):
			return '<a href="%s">%s</a><br>\n' % (url, url)

		l = QVBoxLayout()
		hl.addLayout(l)
		aboutLabel = QLabel()
		aboutLabel.setTextInteractionFlags(Qt.LinksAccessibleByMouse|Qt.TextBrowserInteraction)
		aboutLabel.setOpenExternalLinks(True)
		aboutLabel.setTextFormat(Qt.RichText)
		aboutLabel.setText(lnk("https://github.com/clxjaguar/simple-gcode-generator")
		                   + lnk("https://gitlab.com/cLxJaguar/simple-gcode-generator")
		                   + "<br>"+_("Programmed by")
		                   + " cLx<br>"+lnk("http://clx.freeshell.org/"))
		l.addWidget(aboutLabel)
		ppLabel = QLabel(_("Parent process: %s") % parentProcess)
		ppLabel.setWordWrap(True)
		l.addWidget(ppLabel)
		l.addStretch()
		hl.addStretch()

		iconLabel = QLabel()
		iconLabel.setPixmap(getEmbeddedPixmap())
		hl.addWidget(iconLabel)
		hl.setAlignment(iconLabel, Qt.AlignTop)


class GUI(QWidget):
	def __init__(self):
		QWidget.__init__(self)
		self.filename = None
		self.tabOperations = []
		self.tabOperations.append(OperationHelicoidal())
		self.tabOperations.append(OperationAlternateMilling())
		self.tabOperations.append(OperationPath())
		self.tabOperations.append(OperationDrilling())
		self.tabOperations.append(About())
		self.initUI()

	def initUI(self):
		layout = QVBoxLayout(self)

		def mkQLabel(objectName, text='', alignment=Qt.AlignLeft):
			o = QLabel()
			o.setObjectName(objectName)
			o.setAlignment(alignment)
			o.setText(text)
			return o

		def mkButton(text, function):
			btn = QPushButton(text)
			btn.setFocusPolicy(Qt.TabFocus)
			if function:
				btn.clicked.connect(function)
			return btn

		self.tabOperationsWidget = QTabWidget()
		for tabOperation in self.tabOperations:
			self.tabOperationsWidget.addTab(tabOperation, tabOperation.tabTitle)
		layout.addWidget(self.tabOperationsWidget)

		# global parameters
		l = QGridLayout(); layout.addLayout(l)
		l.addWidget(QLabel(_("Z workpiece surface")))
		self.start_z = MyQDoubleSpinBox(0.0, layout=l, layoutArgs=(0, 1, 1, 2))

		def func():
			if self.start_z.value() < self.end_z.value():
				self.end_z.setValue(self.start_z.value())
		self.start_z.valueChanged.connect(func)

		l.addWidget(QLabel(_("Z at job end")))
		self.end_z = MyQDoubleSpinBox(-10.0, layout=l, layoutArgs=(1, 1, 1, 2))

		def func():
			if self.end_z.value() > self.start_z.value():
				self.start_z.setValue(self.end_z.value())
		self.end_z.valueChanged.connect(func)

		l.addWidget(QLabel(_("Z decrement (height of passes)")))
		self.cutting_depth = MyQDoubleSpinBox(1, minimum=0.05, layout=l, layoutArgs=(2, 1, 1, 2))

		l.addWidget(QLabel(_("Plunging rate")))
		self.plunge_rate = MyQDoubleSpinBox(30, minimum=0, layout=l, layoutArgs=(3, 1, 1, 2))

		l.addWidget(QLabel(_("Feed rate")))
		self.feed_rate = MyQDoubleSpinBox(300, minimum=0, layout=l, layoutArgs=(4, 1, 1, 2))

		l.addWidget(QLabel(_("Trajectory mode")))
		self.trajectoryModeBG = MyQButtonGroup((_("Speed"), _("Exact"), _("Stops")), ("G64", "G61", "G61.1"), 0, layout=l, layoutArgs=(5, 1, 1, 2))

		# buttons at the bottom
		l2 = QHBoxLayout(); layout.addLayout(l2)
		b1 = mkButton(_("Generate G-Code")+"\n"+_("(to file)"), lambda: self.generate())
		l2.addWidget(b1)

		self.updateFileBtn = mkButton(_("Generate G-Code")+"\n"+_("(update file)"), lambda: self.generate(filename=self.filename))
		self.updateFileBtn.setEnabled(False)
		l2.addWidget(self.updateFileBtn)

		keywords = ['bash', 'xfce4-terminal', 'sh -c', 'konsole', 'gnome-terminal']

		for keyword in keywords:
			if keyword in parentProcess:
				b2 = mkButton(_("Generate G-Code")+"\n"+_("(to standard output)"), lambda: self.generate(fd=sys.stdout))
				l2.addWidget(b2)
				break

		self.updateWindowState()
		self.setWindowIcon(getEmbeddedIcon())
		self.show()

	def updateWindowState(self):
		if self.filename != None:
			self.setWindowTitle("%s - %s" % (os.path.basename(self.filename), _("G-Code Generator")))
			self.updateFileBtn.setEnabled(True)
		else:
			self.setWindowTitle("%s (v%s)" % (_("G-Code Generator"), VERSION))
			self.updateFileBtn.setEnabled(False)

	def generate(self, fd=None, filename=None):
		try:
			fnct = self.tabOperationsWidget.currentWidget().generate
			op = self.tabOperationsWidget.currentWidget().tabTitle
			if fnct == None:
				return

			if (fd == None) and (filename != None):
				fd = open(filename, "w")
				self.filename = filename
				self.updateWindowState()

			if (fd == None) and (filename == None):
				dialog = QFileDialog(self, _("Export G-Code as..."))
				dialog.setFilter(dialog.filter() | QDir.Hidden)
				dialog.setDefaultSuffix('ngc')
				dialog.setAcceptMode(QFileDialog.AcceptSave)
				dialog.setNameFilters([_("G-Code files")+' (*.ngc *.nc)', _("All files")+' (*)'])
				if dialog.exec_() == QDialog.Accepted:
					filename = str(dialog.selectedFiles()[0])
					fd = open(filename, "w")
					self.filename = filename
					self.updateWindowState()
				else:
					return

			args={}
			args['start_z']=self.start_z.value()
			args['end_z']=self.end_z.value()
			args['cutting_depth']=self.cutting_depth.value()
			args['plunge_rate']=self.plunge_rate.value()
			args['feed_rate']=self.feed_rate.value()

			fd.write("G90 (absolute programming)\n")
			fd.write("%s (set trajectory mode)\n" % (self.trajectoryModeBG.value()))
			fd.write("G00 Z%g (rapid positioning to 3mm to the surface)\n" % (args['start_z'] + 3))
			fd.write("M03 (spindle ON, clockwise)\n")
			fnct(fd, **args)
			fd.write("M05 (spindle OFF)\n")
			fd.write("G00 Z%g (rapid positioning to 10mm to the surface)\n" % (args['start_z'] + 10))
			fd.write("M30 (end of program)\n")

		except Exception as e:
			QMessageBox.critical(self, _("G-Code generation error"), ("%s:\n%s" % ((_("Exception at line %d") % sys.exc_info()[2].tb_lineno), str(e))))


def main():
	app = QApplication(sys.argv)
	m1 = GUI()
	ret = app.exec_()
	sys.exit(ret)

ICON="iVBORw0KGgoAAAANSUhEUgAAAKcAAACnBAMAAACGOFHfAAAAD1BMVEUAAAAAAABMgIAAubn////R\
      ljXRAAAAAXRSTlMAQObYZgAABFxJREFUaN7Vm1uypCAMhtsdiGQDVs0GrJ4NZA77X9O0dotckhBs\
      8nB4mZqjfv0nICQRHo+suXvtIbXpJnQ2YIpUd78ZCOWlfsNkqe67ZiCUkerceKnT19DZQCgh1bnx\
      1GkIdDYQWkidBkFnA6G5VAvoNAw6GwhNpE4DobOB0Ch1pFC3zgZCV2cA/dg/DYbO44Wuh9RpOHQe\
      b/0BdePbcOh6SP0NUNeChthwCBR2VPHf8JX5wEjTcBmoaKxKbwWF5kNtbAlVdYmErc2HoOxfHltB\
      e0aOdG8KlWX659E2hVUJVGQ+kyY9sOTQoEQmagkX5NAO5iWWccEJhaYzSSqt5QMF7GOy1NR87LE9\
      HwWBg0I385JKeOANxX6mRD2g0OvQ3AGppkUBfT41UpNuvqB4R2gqFWrzbwpNoIVbRags9JneiqX5\
      qBK6lb+zZTMxKqGeNNVTQnNzX1BQCN2Ivxd3owrKWfqhbo6SujSgLPN9qV5g+qCUEVv9ALbN9zzz\
      dXGjAps2lDeebdg0XxLKNGhBfb/QSBoKfdkPIvSG9bvUfypoj9DXWBXffX9H6DkFjoUCiPPpPesx\
      +nQcFBpr1AmFnowHXRxSlNToUkwyHtSMfVRAy9xKYu68FbkIJYQfzqWC3uPCCnQstcvxfD8Bg4Xr\
      nyrqe8exYueT2HM5BSI+/dzfGPoEFs+MB8tIOobbzfepDMyDI6DHL12BluIlzcSGTHKEvoBJ8KZ5\
      85PbQ95hV8qT+Uk1nUQXhDSLLKDNOaqKz0Kls4BictELkUk22nbrQjVes+QsdEP3V9exUMh6VA8t\
      X9vMfMx6VAvd+wFYKOTdpYS+VbI+xXxQq6DUiEqhULzYNDRPAf6SYz8xv5ge4EcB3cgomoc6jVIu\
      4AduOaHfKB6aOgDY1fR8Ml3uIPDQiFgV0LiSJnQx44lQcBKUu+boWfqcT4dAo7lt6KaHQr6cIB/0\
      bfylxro/CArZEo1d4alnfw4toJDGUtgVn/LQHaSCPnugkMSnfTH/COjWAXW4oFiYYe0X40E5O+GT\
      aDHDCDKUTffFgAidWEHzYgGFgcIiQ51c6qGh2IJ6apYXayC7H1GuShIrEr+aRI9ioyirL/QlWSQ0\
      oL4XijkUvqjIFmMUG9VzXe24WE8TKHTWT7kpekmhTLmz2/glzfg6pQolOWh/kPFaJpJQxgFe5U+4\
      StI5tFmclF+lWJJG1ZezlsziSVR+4/NyUhmcAHV9n7GpJH2poerPpnQuTUNbXzmbTMr8fipRTSGg\
      XV95a3ctNLTDsfRnU6Q3DejEctU0ZHci4F0kD21iWWT57lfYwBJ5rzeg76dD9UutzQ0t6Anu2o6i\
      gXa2NVujhkKH75dCg01Yb5eO3TB1ZJGjd8uteG5sHOzS4ZsFT+uH2v/n2tY5cpw60/2nJjtlbfb0\
      /p4tzTY7uk32ntvskjfZz29z8sDmjITJaQ6bcycmJ2RszvKYnDqyOR9lc5LL5MzZqNNx/wFpN3Qb\
      u5c8bgAAAABJRU5ErkJggg=="

def getEmbeddedPixmap():
	qpm = QPixmap()
	qba_s = QByteArray(bytes(ICON.encode()))
	qba = QByteArray.fromBase64(qba_s)
	qpm.convertFromImage(QImage.fromData(qba.data(), 'PNG'))
	return qpm

def getEmbeddedIcon():
	icon = QIcon()
	icon.addPixmap(getEmbeddedPixmap())
	return icon

if __name__ == '__main__':
	main()

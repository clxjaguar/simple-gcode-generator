all: messages.pot fr/LC_MESSAGES/base.mo en/LC_MESSAGES/base.mo

rebuild-mo: clean-mo all
clean-mo:
	rm */LC_MESSAGES/base.mo || true

messages.pot: ../gcode-generator.py
	echo "*** generating messages.pot file from source code ***"
	pygettext3 -d messages ../gcode-generator.py

en/LC_MESSAGES/base.mo: en/LC_MESSAGES/base.po
	echo "*** generating english .mo file ***"
	msgfmt -v en/LC_MESSAGES/base.po -o en/LC_MESSAGES/base.mo

fr/LC_MESSAGES/base.mo: fr/LC_MESSAGES/base.po
	echo "*** generating french .mo file ***"
	msgfmt -v fr/LC_MESSAGES/base.po -o fr/LC_MESSAGES/base.mo

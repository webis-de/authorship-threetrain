#strips spurious OMNI XML-tags and other junk from certain texts in the PAN11 large dataset.
import config
def stripOMNI(text):
	if config.stripOMNI and '<OMNI>' in text:
		while True:
			pos = text.find('<OMNI')
			if pos == -1:
				pos=text.find('</OMNI')
			if pos == -1:
				break
			pos2=text.find('>', pos)
			text =text[:pos] + text[pos2+1:]
		text=text.replace('~',' ')
		text='\n'.join(l.strip() for l in text.split('\n'))
		text=text.replace('\n\n', '.\n\n')
	return text

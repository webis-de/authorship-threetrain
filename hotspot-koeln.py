import requests
import sys
s = requests.Session()
def textBetween(text,pre,suf):
	pre=pre.replace('[\\n]',"\n")
	suf=suf.replace('[\\n]',"\n")
	pos1 = text.find(pre)
	if pos1 == -1:
		raise Exception("'%s' not found" % pre)
	pos1 += len(pre)
	pos2 = text.find(suf,pos1)
	if pos2 == -1:
		raise Exception("'%s' not found" % suf)
	return text[pos1:pos2]
req1 = s.get('http://www.example.org/' ,headers={})
print(req1.text)
data={}
for part in req1.text.split('<input type="hidden"')[1:]:
	print("part:")
	print(part)
	data[textBetween(part,'name="','"')] = textBetween(part,'value="','"')
print('data:',data)
req2 = s.post('https://login.hotspot.koeln/index.cfm',data=data)
print(req2.text)
req3 = s.post('https://login.hotspot.koeln/tariffcheck.cfm',headers={},data={'tariff':'41'})
print(req3.text)
req4 = s.post('https://login.hotspot.koeln/clientdatacheck.cfm',headers={},data={'terms_accepted':'1'})
print(req4.text)
url=textBetween(req4.text,'<input type="button" value="Anmelden" onclick="document.location.href=\'','"')
print("url:",url)
print(s.get(url).text)

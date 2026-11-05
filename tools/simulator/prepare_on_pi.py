from pathlib import Path
import shutil,xml.etree.ElementTree as E,json,hashlib
base=Path('/home/rdp/viessmann/simulator');assert not base.exists(),'Simulator directory already exists'
source=Path('/home/rdp/viessmann/upgrades/v0.98.36/source')
base.mkdir();shutil.copytree(source,base/'source',ignore=shutil.ignore_patterns('.git'))
# Extend upstream's fixed request table with deterministic, explicitly synthetic KW2 reads.
fixtures={'0800':[0xE2,0xFF], '0802':[0x94,0x02], '0804':[0xCC,0x01],
 '2306':[20], '2307':[16], '2308':[22], '6300':[50],
 '0810':[0xC2,0x01], '0812':[0xC2,0x01], '0842':[1],
 '2323':[2], '27D4':[0], '27D3':[14], 'CF30':[0xE8,3,0,0],
 '088A':[0x2D,0x49,1,0], '0896':[0xCF,0], '00F8':[0x20,0x9F]}
p=base/'source/src/vsim.c';s=p.read_text();start=s.index('ctable cmds[] = {');end=s.index('\n};',start)+3
entries=['    { 1, { 0x04 }, 1, { 0x05 } }']
for addr,data in fixtures.items():
 request=[1,0xF7,int(addr[:2],16),int(addr[2:],16),len(data)]
 fmt=lambda vals:', '.join('0x%02X'%v for v in vals)
 entries.append('    { 5, { '+fmt(request)+' }, '+str(len(data))+', { '+fmt(data)+' } }')
s=s[:start]+'ctable cmds[] = {\n'+',\n'.join(entries)+'\n};'+s[end:]
s=s.replace('openSocket(SERVERPORT)','openSocket2(SERVERPORT, "127.0.0.1")')
s=s.replace('    char buf[1] = "\\0";', '    inpidx = 0;\n    char buf[1] = "\\0";')
s=s.replace('                input[inpidx] = buf[i];','                if (inpidx >= (int)sizeof(input)) { return; }\n                input[inpidx] = buf[i];')
p.write_text(s)
(base/'fixtures.json').write_text(json.dumps({'warning':'SYNTHETIC TEST VALUES, NOT REAL CONTROLLER CAPABILITY EVIDENCE','reads':fixtures},indent=2))
config=base/'config';config.mkdir()
main=E.parse('/etc/vcontrold/vcontrold.xml');root=main.getroot()
root.find('./unix/config/serial/tty').text='127.0.0.1:6578'
root.find('./unix/config/net/port').text='3003'
net=root.find('./unix/config/net')
for n in list(net):
 if n.tag=='allow':net.remove(n)
E.SubElement(net,'allow',ip='127.0.0.1')
logging=root.find('./unix/config/logging');logging.find('file').text=str(base/'vcontrold-test.log');logging.find('debug').text='n'
for n in root.iter():
 if n.tag.endswith('include') and n.get('href'):n.set('href',str(config/'vito.xml'))
root.set('xmlns:vcontrol','http://www.openv.de/vcontrol')
main.write(config/'vcontrold.xml',encoding='utf-8',xml_declaration=True)
# Read-only snapshot: deliberately exclude ALL setaddr operations, even in simulation.
vito=E.parse('/etc/vcontrold/vito.xml');commands=vito.getroot().find('commands')
for c in list(commands):
 if c.get('protocmd')!='getaddr':commands.remove(c)
vito.write(config/'vito.xml',encoding='utf-8',xml_declaration=True)
assert not list(config.rglob('*ttyUSB*'))
(base/'production-before.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path('/etc/vcontrold/vito.xml'),Path('/etc/vcontrold/vcontrold.xml'),Path('/usr/local/sbin/vcontrold'))},indent=2))
print('Prepared isolated simulator sources, fixtures, read-only XML, and production checksums.')

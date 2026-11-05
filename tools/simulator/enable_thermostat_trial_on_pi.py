from pathlib import Path
import xml.etree.ElementTree as E,shutil
base=Path('/home/rdp/viessmann/simulator');p=base/'source/src/vsim.c'
backup=p.with_suffix('.c.before-thermostat');assert not backup.exists();shutil.copy2(p,backup)
s=p.read_text();needle='                for ( j = 0 ; j < cmdc; j++) {';assert s.count(needle)==1
insert='''                /* Synthetic KW2 single-byte target writes: update matching read fixture. */
                if (inpidx == 6 && (unsigned char)input[0] == 0x01 &&
                    (unsigned char)input[1] == 0xf4 && (unsigned char)input[4] == 1) {
                    unsigned int addr = ((unsigned char)input[2] << 8) | (unsigned char)input[3];
                    if (addr == 0x2306 || addr == 0x2307 || addr == 0x2308 || addr == 0x6300) {
                        for (j = 0; j < cmdc; j++) {
                            if (cmds[j].cmdlen == 5 && (unsigned char)cmds[j].cmd[1] == 0xf7 &&
                                cmds[j].cmd[2] == input[2] && cmds[j].cmd[3] == input[3]) {
                                cmds[j].rsp[0] = input[5];
                            }
                        }
                        char ack = 0;
                        writen(fd, &ack, 1);
                        inpidx = 0;
                        i++;
                        continue;
                    }
                }
'''
s=s.replace(needle,insert+needle);p.write_text(s)
p=base/'config/vito.xml';shutil.copy2(p,p.with_suffix('.xml.before-thermostat'))
tree=E.parse(p);root=tree.getroot()
root.find('./devices/device[@ID="209F"]').set('name','SIMULATOR_209F')
commands=root.find('commands')
# Only four synthetic setter definitions are enabled in this separate test XML.
for name,addr in [('setTempRaumNorSollM1','2306'),('setTempRaumRedSollM1','2307'),('setTempPartyM1','2308'),('setTempWWsoll','6300')]:
 c=E.SubElement(commands,'command',name=name,protocmd='setaddr');E.SubElement(c,'addr').text=addr;E.SubElement(c,'len').text='1';E.SubElement(c,'unit').text='ST';E.SubElement(c,'description').text='SIMULATOR ONLY target write'
tree.write(p,encoding='utf-8',xml_declaration=True)
print('Prepared simulator-only identity and four stateful target setters.')

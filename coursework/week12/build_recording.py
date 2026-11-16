from pathlib import Path
import json, html
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
BASE=Path(__file__).resolve().parent
src=json.loads((BASE/'recording-script.json').read_text())
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Talk',fontName='Times-Roman',fontSize=15,leading=21,spaceAfter=13))
styles.add(ParagraphStyle(name='TalkHead',fontName='Times-Bold',fontSize=14,leading=18,spaceBefore=14,spaceAfter=10))
styles.add(ParagraphStyle(name='NoteSmall',fontName='Times-Roman',fontSize=10,leading=13,spaceAfter=9,textColor=colors.HexColor('#444444')))
md=['# '+src['title'],'',src['status'],'',src['timing'],'','Roles below are suggested. Both students must understand, rehearse and perform their own parts. Read only spoken paragraphs. Screen notes are not spoken.','']
counts={}
for speaker in ['Jesse Zhang','Yongqi Sheng']:
    sections=[s for s in src['sections'] if s['speaker']==speaker]
    counts[speaker]=sum(len(s['text'].split()) for s in sections)
    story=[Paragraph(html.escape(speaker)+' - Week 12',styles['Title']),Paragraph('Prepared recording script. Suggested timing, not a completed recording.',styles['NoteSmall'])]
    for s in sections:
        md += ['## '+s['speaker']+' | '+s['time']+' | '+s['heading'],'','Screen action (not spoken): '+s['screen'],'',s['text'],'']
        story += [Paragraph(s['time']+' | '+html.escape(s['heading']),styles['TalkHead']),Paragraph(html.escape(s['text']),styles['Talk'])]
    def footer(c,d):
        c.setFont('Times-Roman',9); c.drawString(48,28,'DS 340W | Suggested speaker allocation');c.drawRightString(564,28,str(d.page))
    SimpleDocTemplate(str(BASE/(speaker.split()[0]+'-speaker.pdf')),pagesize=(612,792),rightMargin=48,leftMargin=48,topMargin=44,bottomMargin=46).build(story,onFirstPage=footer,onLaterPages=footer)
(BASE/'recording-script.md').write_text('\n'.join(md))
(BASE/'speaker-word-counts.json').write_text(json.dumps(counts,indent=2)+'\n')
print(counts)

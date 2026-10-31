from html.parser import HTMLParser
from html import escape
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
for name, filename in [('Body','DejaVuSans.ttf'),('Body-Bold','DejaVuSans-Bold.ttf'),('Body-Italic','DejaVuSans-Oblique.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Body-Bold', italic='Body-Italic', boldItalic='Body-Bold')
ink, blue, muted = colors.HexColor('#172535'), colors.HexColor('#175f79'), colors.HexColor('#526273')
base = ParagraphStyle('base', fontName='Body', fontSize=10, leading=15, spaceAfter=10, textColor=ink, alignment=TA_LEFT)
styles = {
    'p': base,
    'h1': ParagraphStyle('title', parent=base, fontName='Body-Bold', fontSize=25, leading=31, spaceAfter=19, keepWithNext=True),
    'eyebrow': ParagraphStyle('eyebrow', parent=base, fontName='Body-Bold', fontSize=9, leading=13, textColor=blue, keepWithNext=True),
    'lead': ParagraphStyle('lead', parent=base, fontSize=13, leading=19, spaceAfter=16),
    'section': ParagraphStyle('section', parent=base, fontName='Body-Bold', fontSize=16, leading=22, spaceBefore=19, spaceAfter=12, keepWithNext=True),
    'label': ParagraphStyle('label', parent=base, fontName='Body-Bold', fontSize=12, leading=18, spaceBefore=10, spaceAfter=9, textColor=blue, keepWithNext=True),
    'note': ParagraphStyle('note', parent=base, fontSize=8.6, leading=13, textColor=muted),
    'ref': ParagraphStyle('ref', parent=base, fontSize=8.6, leading=13, spaceAfter=9),
    'callout': ParagraphStyle('callout', parent=base, backColor=colors.HexColor('#edf5f7'), borderColor=blue, borderWidth=.7, borderPadding=10, spaceBefore=8, spaceAfter=18),
    'footer': ParagraphStyle('footer', parent=base, fontSize=8.5, leading=13, textColor=muted, spaceBefore=15),
}

class Extract(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.main=False; self.active=None; self.parts=[]; self.blocks=[]
    def handle_starttag(self, tag, attrs):
        data=dict(attrs)
        if tag=='main': self.main=True
        if not self.main: return
        if tag in ('p','h1'):
            self.active=(tag,data.get('class',tag)); self.parts=[]
        elif self.active:
            if tag in ('b','i'): self.parts.append('<'+tag+'>')
            elif tag=='a': self.parts.append('<a href="'+escape(data.get('href',''),quote=True)+'" color="#175f79">')
            elif tag=='code': self.parts.append('<font face="Courier" size="9">')
            elif tag=='br': self.parts.append('<br/>')
    def handle_endtag(self, tag):
        if tag in ('p','h1') and self.active:
            self.blocks.append((self.active[1], ''.join(self.parts)))
            self.active=None
        elif self.active:
            if tag in ('b','i','a'): self.parts.append('</'+tag+'>')
            elif tag=='code': self.parts.append('</font>')
        if tag=='main': self.main=False
    def handle_data(self,data):
        if self.active: self.parts.append(escape(data))

parsed=Extract(); parsed.feed((ROOT/'research.html').read_text())
story=[Paragraph(text, styles.get(kind,base)) for kind,text in parsed.blocks]
def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#d7e0e5'))
    canvas.line(48,40,564,40)
    canvas.setFont('Body',8)
    canvas.setFillColor(muted)
    canvas.drawString(48,26,'ConvMem research • 31 October 2026')
    canvas.drawRightString(564,26,str(doc.page))
doc=SimpleDocTemplate(str(ROOT/'convmem-research.pdf'),pagesize=letter,rightMargin=48,leftMargin=48,topMargin=47,bottomMargin=55,title='ConvMem: reliable memory for work across your PC',author='Research assessment')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(f'Created PDF from {len(parsed.blocks)} paragraphs')

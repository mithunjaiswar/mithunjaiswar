import json
R="raw_pilot_week!"
def rr(c): return "r_"+c
def v(x):
    if isinstance(x,(int,float)): return {"userEnteredValue":{"numberValue":x}}
    if isinstance(x,str) and x.startswith("="): return {"userEnteredValue":{"formulaValue":x}}
    if x is None: return {}
    return {"userEnteredValue":{"stringValue":x}}
def cells(sid,r,c,rows):  # r,c 0-based
    return {"updateCells":{"rows":[{"values":[v(x) for x in row]} for row in rows],"fields":"userEnteredValue","start":{"sheetId":sid,"rowIndex":r,"columnIndex":c}}}
def grid(sid,r1,r2,c1,c2): return {"sheetId":sid,"startRowIndex":r1,"endRowIndex":r2,"startColumnIndex":c1,"endColumnIndex":c2}
def fmt(sid,r1,r2,c1,c2,f,fields):
    return {"repeatCell":{"range":grid(sid,r1,r2,c1,c2),"cell":{"userEnteredFormat":f},"fields":fields}}
def numfmt(sid,r1,r2,c1,c2,pat,typ="NUMBER"):
    return fmt(sid,r1,r2,c1,c2,{"numberFormat":{"type":typ,"pattern":pat}},"userEnteredFormat.numberFormat")
def rgb(h): h=h.lstrip('#'); return {"red":int(h[0:2],16)/255,"green":int(h[2:4],16)/255,"blue":int(h[4:6],16)/255}
def style(sid,r1,r2,c1,c2,bg=None,bold=None,color=None,size=None,align=None,wrap=None,italic=None):
    f={};fl=[]
    tf={}
    if bold is not None: tf["bold"]=bold
    if italic is not None: tf["italic"]=italic
    if size: tf["fontSize"]=size
    if color: tf["foregroundColorStyle"]={"rgbColor":rgb(color)}
    if tf: f["textFormat"]=tf; fl.append("userEnteredFormat.textFormat")
    if bg: f["backgroundColorStyle"]={"rgbColor":rgb(bg)}; fl.append("userEnteredFormat.backgroundColorStyle")
    if align: f["horizontalAlignment"]=align; fl.append("userEnteredFormat.horizontalAlignment")
    if wrap: f["wrapStrategy"]=wrap; fl.append("userEnteredFormat.wrapStrategy")
    return fmt(sid,r1,r2,c1,c2,f,",".join(fl))
def width(sid,c1,c2,px): return {"updateDimensionProperties":{"range":{"sheetId":sid,"dimension":"COLUMNS","startIndex":c1,"endIndex":c2},"properties":{"pixelSize":px},"fields":"pixelSize"}}
def height(sid,r1,r2,px): return {"updateDimensionProperties":{"range":{"sheetId":sid,"dimension":"ROWS","startIndex":r1,"endIndex":r2},"properties":{"pixelSize":px},"fields":"pixelSize"}}
def hide_rows(sid,r1,r2): return {"updateDimensionProperties":{"range":{"sheetId":sid,"dimension":"ROWS","startIndex":r1,"endIndex":r2},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}}
def hide_cols(sid,c1,c2): return {"updateDimensionProperties":{"range":{"sheetId":sid,"dimension":"COLUMNS","startIndex":c1,"endIndex":c2},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}}
def dv_range(sid,r,c,src):
    return {"setDataValidation":{"range":grid(sid,r,r+1,c,c+1),"rule":{"condition":{"type":"ONE_OF_RANGE","values":[{"userEnteredValue":src}]},"strict":True,"showCustomUi":True}}}
def border(sid,r1,r2,c1,c2,col="#BDBDBD"):
    b={"style":"SOLID","width":1,"colorStyle":{"rgbColor":rgb(col)}}
    return {"updateBorders":{"range":grid(sid,r1,r2,c1,c2),"top":b,"bottom":b,"left":b,"right":b,"innerHorizontal":b,"innerVertical":b}}
def merge(sid,r1,r2,c1,c2): return {"mergeCells":{"range":grid(sid,r1,r2,c1,c2),"mergeType":"MERGE_ALL"}}
def cf_scale(sid,r1,r2,c1,c2,low="#FFFFFF",high="#F4C7C3"):
    return {"addConditionalFormatRule":{"rule":{"ranges":[grid(sid,r1,r2,c1,c2)],"gradientRule":{"minpoint":{"colorStyle":{"rgbColor":rgb(low)},"type":"MIN"},"maxpoint":{"colorStyle":{"rgbColor":rgb(high)},"type":"MAX"}}},"index":0}}
NAVY="#1F3864"; LBLUE="#DCE6F1"; GREY="#F2F2F2"; YEL="#FFF2CC"; RED="#C00000"; GREEN="#E2EFDA"; PINK="#FCE4E4"
# filter bar: row index 1 (row 2): A City B, C Product D, E SD F, G Habit H, I ELC J
def filter_bar(sid, include_sd=True):
    rq=[]
    items=[("City","B"),("Product","D"),("SD Bucket","F"),("Payment Habit","H"),("ELC / Non ELC","J")]
    srcs={"City":"=lists!$B$2:$B$30","Product":"=lists!$A$2:$A$30","SD Bucket":"=lists!$C$2:$C$30","Payment Habit":"=lists!$D$2:$D$30","ELC / Non ELC":"=lists!$E$2:$E$5"}
    row=[]
    for i,(lab,col) in enumerate(items):
        if lab=="SD Bucket" and not include_sd: row+=["",""]; continue
        row+=[lab+" ▸","All"]
    rq.append(cells(sid,1,0,[row]))
    for i,(lab,col) in enumerate(items):
        if lab=="SD Bucket" and not include_sd: continue
        rq.append(dv_range(sid,1,2*i+1,srcs[lab]))
        rq.append(style(sid,1,2,2*i,2*i+1,bg=GREY,bold=True,align="RIGHT"))
        rq.append(style(sid,1,2,2*i+1,2*i+2,bg=YEL,bold=True,align="CENTER"))
    return rq
OK="DD"
def F(city=None, ok=None):
    c = city if city else 'IF($B$2="All","*",$B$2)'
    return f'r_B,{c},r_{ok or OK},1'
def title(sid,text,sub):
    return [cells(sid,0,0,[[text]]), cells(sid,2,0,[[sub]]),
            style(sid,0,1,0,16,bg=NAVY,bold=True,color="#FFFFFF",size=14),
            style(sid,2,3,0,16,italic=True,color="#595959"), height(sid,0,1,34)]
def section(sid,r,text,c2=14):
    return [cells(sid,r,0,[[text]]), style(sid,r,r+1,0,c2,bg=LBLUE,bold=True,color=NAVY,size=11)]
def paste(sid,r,c1,c2,r2):  # copy row r cols c1:c2 to rows r+1..r2-1
    return {"copyPaste":{"source":grid(sid,r,r+1,c1,c2),"destination":grid(sid,r+1,r2,c1,c2),"pasteType":"PASTE_FORMULA"}}
def pastec(sid,r1,r2,c,c2):  # copy col c to c+1..c2-1
    return {"copyPaste":{"source":grid(sid,r1,r2,c,c+1),"destination":grid(sid,r1,r2,c+1,c2),"pasteType":"PASTE_FORMULA"}}

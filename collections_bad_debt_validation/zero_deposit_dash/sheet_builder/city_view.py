# City_View (daily, WBR View V2 format): product segments across (last 4 days + DoD each), metric blocks down, cities in rows
import json
S=121
SEG=[("All","*"),("Leasing - Single","Leasing - Single"),("Leasing - EIP","Leasing - EIP"),("D2O","D2O"),("Own Now","Own Now"),("EV_Leasing","EV_Leasing"),("EV_D2O","EV_D2O")]
CITIES=["Mumbai","Kolkata","Bangalore","Delhi NCR","Hyderabad","Chennai","Pune"]
def B(r): return f'raw!$A$2:$A,C$5-WEEKDAY(C$5,3),raw!$B$2:$B,$A{r},raw!$CN$2:$CN,C$4,raw!$EU$2:$EU,"Include"'
K='WEEKDAY(C$5,2)'
I=lambda a,b: f'INDEX(raw!${a}$2:${b},0,{K})'
M=[("Active pilots",lambda r:f'=COUNTIFS({B(r)},{I("AH","AN")},">-1E+15")',"n"),
("Live OS - pending at day end (Rs)",lambda r:f'=-SUMIFS({I("AH","AN")},{B(r)},{I("AH","AN")},"<0")',"n"),
("Collection that day (Rs)",lambda r:f'=SUMIFS({I("AO","AU")},{B(r)})',"n"),
("Critical - day end",lambda r:f'=COUNTIFS({B(r)},{I("DO","DU")},1)',"n"),
("Critical - NOT called",lambda r:f'=COUNTIFS({B(r)},{I("DH","DN")},1,{I("BX","CD")},0)',"n"),
("New car recovery raised that day",lambda r:f'=COUNTIFS({B(r)},raw!$Z$2:$Z,C$5)',"n"),
("Needed car recovery (Live OS >= deposit, no recovery)",lambda r:f'=COUNTIFS({B(r)},{I("BC","BI")},1)-COUNTIFS({B(r)},{I("BC","BI")},1,raw!$Z$2:$Z,"<="&C$5)',"n"),
("Active bad debt amount (Rs)",lambda r:f'=SUMIFS({I("EN","ET")},{B(r)},{I("EG","EM")},1)',"n"),
("Non-active bad debt amount (Rs)",lambda r:f'=SUMIFS({I("EN","ET")},{B(r)},{I("EG","EM")},2)',"n")]
R0=7; BS=11
vals={}  # A1 -> 2D
def col(i):
  s='';i+=1
  while i: i,r=divmod(i-1,26); s=chr(65+r)+s
  return s
row3=[];row4=[];row5=[]
for si,(nm,crit) in enumerate(SEG):
  row3+= [nm,"","","",""]; row4+=[crit]*4+[""]
  row5+= (["=F5-3","=F5-2","=F5-1","=TODAY()-WEEKDAY(TODAY(),3)+lists!$R$10-1","DoD"] if si==0 else ["=$C$5","=$D$5","=$E$5","=$F$5","DoD"])
last=col(2+5*len(SEG)-1)
vals["B1"]=[["Zero & Low Deposit - City x Product daily comparison (last 4 days)"]]
vals["B2"]=[["Excludes Exclusions list. Bad debt fills from SQL refresh."]]
vals[f"C3:{last}5"]=[row3,row4,row5]
vals["B5"]=[["City"]]
blocks=[]
for mi,(name,f,kind) in enumerate(M):
  r=R0+mi*BS; blocks.append((r,kind))
  vals[f"B{r}"]=[[name]]
  vals[f"B{r+1}:G{r+1}"]=[["City","=C$5","=D$5","=E$5","=F$5","DoD"]]
  vals[f"A{r+2}:C{r+2}"]=[["*","All",f(r+2)]]
  vals[f"G{r+2}"]=[[f'=IFERROR((F{r+2}-E{r+2})/ABS(E{r+2}),"-")']]
vals["A10:B16"]=[[c,c] for c in CITIES]
def g(r1,r2,c1,c2): return {"sheetId":S,"startRowIndex":r1,"endRowIndex":r2,"startColumnIndex":c1,"endColumnIndex":c2}
rq=[]
for mi,(r,kind) in enumerate(blocks):
  a=r+1  # 0-based index of All row (sheet row r+2)
  rq.append({"copyPaste":{"source":g(a,a+1,2,3),"destination":g(a+1,a+8,2,3),"pasteType":"PASTE_FORMULA"}})
  rq.append({"copyPaste":{"source":g(R0+1,R0+2,6,7),"destination":g(a,a+8,6,7),"pasteType":"PASTE_FORMULA"}})
  if mi: rq.append({"copyPaste":{"source":g(9,16,0,2),"destination":g(a+1,a+8,0,2),"pasteType":"PASTE_VALUES"}})
end=R0+len(M)*BS
rq.append({"copyPaste":{"source":g(R0-1,end,2,3),"destination":g(R0-1,end,3,6),"pasteType":"PASTE_FORMULA"}})
for si in range(1,len(SEG)):
  rq.append({"copyPaste":{"source":g(R0-1,end,2,7),"destination":g(R0-1,end,2+5*si,7+5*si),"pasteType":"PASTE_FORMULA"}})
fmt=[]
nc=2+5*len(SEG)
fmt.append({"repeatCell":{"range":g(0,end,0,nc),"cell":{"userEnteredFormat":{"textFormat":{"fontSize":9},"verticalAlignment":"MIDDLE","horizontalAlignment":"CENTER"}},"fields":"userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment"}})
fmt.append({"repeatCell":{"range":g(0,end,1,2),"cell":{"userEnteredFormat":{"horizontalAlignment":"LEFT"}},"fields":"userEnteredFormat.horizontalAlignment"}})
fmt.append({"repeatCell":{"range":g(R0,end,2,nc),"cell":{"userEnteredFormat":{"numberFormat":{"type":"NUMBER","pattern":"#,##0;-#,##0;0"}}},"fields":"userEnteredFormat.numberFormat"}})
fmt.append({"repeatCell":{"range":g(0,1,1,nc),"cell":{"userEnteredFormat":{"backgroundColorStyle":{"rgbColor":{"red":0.12,"green":0.22,"blue":0.39}},"textFormat":{"bold":True,"fontSize":12,"foregroundColorStyle":{"rgbColor":{"red":1,"green":1,"blue":1}}},"horizontalAlignment":"LEFT"}},"fields":"userEnteredFormat"}})
fmt.append({"repeatCell":{"range":g(2,3,2,nc),"cell":{"userEnteredFormat":{"textFormat":{"bold":True,"fontSize":10}}},"fields":"userEnteredFormat.textFormat"}})
fmt.append({"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"ROWS","startIndex":3,"endIndex":4},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}})
fmt.append({"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":0,"endIndex":1},"properties":{"hiddenByUser":True},"fields":"hiddenByUser"}})
fmt.append({"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":1,"endIndex":2},"properties":{"pixelSize":250},"fields":"pixelSize"}})
fmt.append({"updateDimensionProperties":{"range":{"sheetId":S,"dimension":"COLUMNS","startIndex":2,"endIndex":nc},"properties":{"pixelSize":78},"fields":"pixelSize"}})
# date / DoD formats via CF-free direct ranges
for si in range(len(SEG)):
  c=2+5*si
  fmt.append({"repeatCell":{"range":g(R0,end,c+4,c+5),"cell":{"userEnteredFormat":{"numberFormat":{"type":"NUMBER","pattern":"+0%;-0%;0%"},"borders":{"right":{"style":"SOLID_MEDIUM","colorStyle":{"rgbColor":{"red":0.4,"green":0.4,"blue":0.4}}}}}},"fields":"userEnteredFormat.numberFormat,userEnteredFormat.borders"}})
  fmt.append({"repeatCell":{"range":g(4,5,c,c+4),"cell":{"userEnteredFormat":{"numberFormat":{"type":"DATE","pattern":"dd-mmm"},"textFormat":{"bold":True}}},"fields":"userEnteredFormat.numberFormat,userEnteredFormat.textFormat"}})
cf=[{"addConditionalFormatRule":{"rule":{"ranges":[g(R0,end,1,nc)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":'=$B8="City"'}]},"format":{"backgroundColorStyle":{"rgbColor":{"red":0.235,"green":0.471,"blue":0.847}},"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":{"red":1,"green":1,"blue":1}}},"numberFormat":{"type":"DATE","pattern":"dd-mmm"}}}},"index":0}},
 {"addConditionalFormatRule":{"rule":{"ranges":[g(R0,end,1,nc)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":'=$B8="All"'}]},"format":{"backgroundColorStyle":{"rgbColor":{"red":0.863,"green":0.902,"blue":0.945}},"textFormat":{"bold":True}}}},"index":1}},
 {"addConditionalFormatRule":{"rule":{"ranges":[g(R0,end,1,2)],"booleanRule":{"condition":{"type":"CUSTOM_FORMULA","values":[{"userEnteredValue":'=AND($B8<>"",$B9="City")'}]},"format":{"textFormat":{"bold":True,"foregroundColorStyle":{"rgbColor":{"red":0.12,"green":0.22,"blue":0.39}}}}}},"index":2}}]
json.dump({"vals":vals,"rq":rq,"fmt":fmt+cf,"nc":nc,"end":end},open('city_view.json','w'))
print(nc,end,len(rq),len(fmt+cf))

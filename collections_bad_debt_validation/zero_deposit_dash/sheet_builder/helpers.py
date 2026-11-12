import json
# helper cols starting CN (index 91)
N=lambda rng: f'IFERROR({rng}*1,0)'
ones='SEQUENCE(7,1,1,0)'
pick=lambda rng: f'MMULT({N(rng)}*(SEQUENCE(1,7)=CO2:CO),{ones})'
isn=lambda rng: f'MMULT(ISNUMBER({rng})*(SEQUENCE(1,7)=CO2:CO),{ones})'
H=[
("Product (EIP split)", '=ARRAYFORMULA(IF(A2:A="","",IF(C2:C="Leasing",IF(E2:E="EIP","Leasing - EIP","Leasing - Single"),C2:C)))'),
("Latest Day #", '=ARRAYFORMULA(IF(A2:A="","",IF(A2:A=TODAY()-WEEKDAY(TODAY(),3),WEEKDAY(TODAY(),2),7)))'),
("Active Latest Day (1/0)", f'=ARRAYFORMULA(IF(A2:A="","",{isn("AH2:AN")}))'),
("Owed Latest Day (Rs)", f'=ARRAYFORMULA(IF(A2:A="","",MAX(0,0)*0+IF(-{pick("AH2:AN")}>0,-{pick("AH2:AN")},0)))'),
("Surpassed Latest Day (1/0)", f'=ARRAYFORMULA(IF(A2:A="","",{pick("BC2:BI")}))'),
("Critical AM Latest Day (1/0)", f'=ARRAYFORMULA(IF(A2:A="","",{pick("BJ2:BP")}))'),
("Critical EOD Latest Day (1/0)", f'=ARRAYFORMULA(IF(A2:A="","",{pick("BQ2:BW")}))'),
("Attempts Latest Day", f'=ARRAYFORMULA(IF(A2:A="","",{pick("BX2:CD")}))'),
("Attempts Week", f'=ARRAYFORMULA(IF(A2:A="","",MMULT({N("BX2:CD")},{ones})))'),
("Connects Week", f'=ARRAYFORMULA(IF(A2:A="","",MMULT({N("CE2:CK")},{ones})))'),
("Surpassed Any Day (1/0)", f'=ARRAYFORMULA(IF(A2:A="","",--(MMULT({N("BC2:BI")},{ones})>0)))'),
("Collection Latest Day", f'=ARRAYFORMULA(IF(A2:A="","",{pick("AO2:AU")}))'),
("Unsecured Exposure (owed above deposit)", '=ARRAYFORMULA(IF(A2:A="","",IF(CQ2:CQ-IF(ISNUMBER(I2:I),IF(I2:I>0,I2:I,0),0)>0,CQ2:CQ-IF(ISNUMBER(I2:I),IF(I2:I>0,I2:I,0),0),0)))'),
("Join Week", '=ARRAYFORMULA(IF(A2:A="","",IF(ISNUMBER(V2:V),V2:V-WEEKDAY(V2:V,3),"")))'),
("Days Since Join", '=ARRAYFORMULA(IF(A2:A="","",IF(ISNUMBER(V2:V),A2:A+CO2:CO-1-V2:V,"")))'),
("Stage Today", '=ARRAYFORMULA(IF(A2:A="","",IF(Y2:Y="Closed","6. Car Recovery Closed",IF(Y2:Y="Open","5. In Car Recovery",IF(CP2:CP=0,"0. Not Active",IF(CR2:CR=1,"4. Owes >= Deposit - START RECOVERY",IF(CT2:CT=1,"3. Critical - owes >= 1 day rent",IF(CQ2:CQ>0,"2. Owes < 1 day rent","1. Paid Up"))))))))'),
]
# fix owed formula simpler
p=pick("AH2:AN")
H[3]=("Owed Latest Day (Rs)", f'=ARRAYFORMULA(IF(A2:A="","",LET(x,-{p},IF(x>0,x,0))))')
cols=[]
def col(i):
  s='';i+=1
  while i: i,r=divmod(i-1,26); s=chr(65+r)+s
  return s
for k,(h,f) in enumerate(H): cols.append((col(91+k),h,f))
for c,h,f in cols: print(c,h)
req=[]
for k,(h,f) in enumerate(H):
  req.append({"updateCells":{"rows":[{"values":[{"userEnteredValue":{"stringValue":h}}]},{"values":[{"userEnteredValue":{"formulaValue":f}}]}],"fields":"userEnteredValue","start":{"sheetId":0,"rowIndex":0,"columnIndex":91+k}}})
json.dump(req,open('helpers.json','w'))

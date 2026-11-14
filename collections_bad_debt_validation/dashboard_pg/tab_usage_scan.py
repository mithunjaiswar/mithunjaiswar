import json,re,sys,collections
titles=["Gap_Reason","Raw_Data","Updated At","WBR View","WBR View V2","D2O_Deposit_Bucket","Summary","Copy of Summary 2","notpaid_list","OwnNow Analysis","attrition_data","Ownership_Dash","ownnow_highrisk","Updated at / Resources","advance_payment_data","NonFunnel_BadDebt_Collected","sd_bucket","sd_bucket_V2","OS_Surpass","excellent_data","Readme!","City_Targets","Action Items","SD_Profiles","Collection_Trend [Deposit]","City_Deepdive","Collection_Trend [Tenure]","SD_Profiles [At Allocation]","SD_Tenure_Mix View","Country_Collection_RCA","City_Collection_RCA","CarryForward_View","City Deepdive [AI]","Dash Roadmap","Deck_CityView","Query","last_updated","filter","Ownership_CR_Import","D2O_Bucket_HowToUpdate","D2O_City_Comparison","Exclusions"]
out=collections.defaultdict(collections.Counter); nform=collections.Counter(); imp=collections.defaultdict(set)
seen=set()
for f in sys.argv[1:]:
    d=json.load(open(f))
    for s in d['content']['sheets']:
        t=s['properties']['title']
        if (t,f) in seen: pass
        for dd in s.get('data',[]):
            for r in dd.get('rowData',[]) or []:
                for v in r.get('values',[]) or []:
                    fm=v.get('userEnteredValue',{}).get('formulaValue')
                    if not fm: continue
                    nform[t]+=1
                    for m in re.findall(r'IMPORTRANGE\(\s*"([^"]+)"\s*,\s*"([^"!]+)',fm): imp[t].add(m[0][:12]+'..:'+m[1])
                    for o in titles:
                        if o==t: continue
                        if ("'"+o+"'!") in fm or (re.search(r'(?<![\w\'])'+re.escape(o)+r'!',fm) and ' ' not in o):
                            out[o][t]+=1
json.dump({"inc":{k:dict(v) for k,v in out.items()},"nform":dict(nform),"imp":{k:list(v) for k,v in imp.items()}},open('tabs.json','w'))
for t in titles: print(t,'| formulas',nform.get(t,0),'| used by',dict(out.get(t,{})),'| import',list(imp.get(t,[])))

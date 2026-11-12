# test version of raw_pilot_week.sql for a few ETMs (DB MCP has a 60 s limit)
import re, sys
lst = ','.join("'%s'" % e for e in sys.argv[1].split(','))
s = open('raw_pilot_week.sql').read()
a = "  where m.for_collections = 1 and m.hissab_week in (select wk from wk)\n"
assert s.count(a) == 1; s = s.replace(a, a.rstrip('\n') + " and m.partner_etm in (%s)\n" % lst)
b = "  where h.date >= (select w0 from p) and h.date <= current_date and h.is_active = 1\n"
assert s.count(b) == 1; s = s.replace(b, b.rstrip('\n') + " and h.driver_id in (select id from fleet_driver where employee_id in (%s))\n" % lst)
s = '\n'.join(re.sub(r'\s*--.*$', '', l) for l in s.split('\n'))
print('\n'.join(l for l in s.split('\n') if l.strip()))

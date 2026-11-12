# Build a test version of mastertab.sql for a few partners (DB MCP has a 60 s limit).
import re, sys
etms = sys.argv[1].split(',')
src = sys.argv[2] if len(sys.argv) > 2 else 'mastertab.sql'
s = open(src).read()
old = "  select act.etm, act.city, act.product, 0 from act where act.etm not in (select etm from cl)\n),"
assert s.count(old) == 1
s = s.replace(old, old[:-3] + "\n),\npop_t as (select * from pop0 where etm in (%s))," % ','.join("'%s'" % e for e in etms))
s = s.replace("pop as materialized (", "pop0 as materialized (", 1)
s = s.replace("pop_t as (", "pop as materialized (", 1)
s = '\n'.join(re.sub(r'\s*--.*$', '', l) for l in s.split('\n'))
print('\n'.join(l for l in s.split('\n') if l.strip()))

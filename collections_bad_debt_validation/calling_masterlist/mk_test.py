# Build a one-line test version of mastertab.sql for a few partners (DB MCP has a 60 s limit).
import re, sys
etms = sys.argv[1].split(',')
s = open('mastertab.sql').read()
s = s.replace("  from pop\n  join lateral", "  from (select * from pop where etm in (%s)) pop\n  join lateral" % ','.join("'%s'" % e for e in etms))
s = '\n'.join(re.sub(r'\s*--.*$', '', l) for l in s.split('\n'))
print('\n'.join(l for l in s.split('\n') if l.strip()))

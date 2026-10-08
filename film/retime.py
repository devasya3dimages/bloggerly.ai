import re, json
vo = json.load(open('audio/vo.json'))['dur']
OLD = [0, 3, 7.2, 11.4, 13.4, 17.6, 21.8, 26, 31, 34.4, 40]
PAD = [1.0, 0.45, 0.35, 0.35, 0.65, 0.5, 0.5, 0.75, 0.6, 1.4]
new = [0.0]
for d, p in zip(vo, PAD): new.append(round(new[-1] + d + p, 3))
def seg(t):
    for k in range(10):
        if OLD[k] <= t < OLD[k+1]: return k
    return 9
def mp(t, k=None):
    k = seg(t) if k is None else k
    a, b, A, B = OLD[k], OLD[k+1], new[k], new[k+1]
    return round(A + (t - a) * (B - A) / (b - a), 3)
s = open('film.html').read()
def fix(m):
    tag = m.group(0)
    i0 = re.search(r'data-in="([\d.]+)"', tag); k = seg(float(i0.group(1)))
    f = (new[k+1]-new[k]) / (OLD[k+1]-OLD[k])
    tag = re.sub(r'data-in="([\d.]+)"', lambda x: f'data-in="{mp(float(x.group(1)), k)}"', tag)
    tag = re.sub(r'data-out="([\d.]+)"', lambda x: x.group(0) if float(x.group(1)) > 50 else f'data-out="{mp(min(float(x.group(1)), OLD[k+1]-0.01), k)}"', tag)
    tag = re.sub(r'data-(st|dur)="([\d.]+)"', lambda x: f'data-{x.group(1)}="{round(float(x.group(2))*min(f,1.0),3)}"', tag)
    return tag
s = re.sub(r'<(div|span)[^>]*data-in="[^>]*>', fix, s)
s = s.replace('const DUR = 40;', f'const DUR = {new[-1]};')
open('film_fast.html', 'w').write(s)
json.dump({'scenes': new, 'vo_start': [round(n + (0.35 if i else 0.45), 3) for i, n in enumerate(new[:-1])]}, open('timeline.json', 'w'))
print(new)
